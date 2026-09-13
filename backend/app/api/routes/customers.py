"""Customers worth investigating: the book of lost / at-risk renewals.

seed: the demo fixtures. live: Stripe subscriptions that are canceled or failing (past_due,
incomplete, unpaid), read with the user's stored Stripe key. Each row carries the latest
investigation for that customer (when Postgres is configured) so the UI can show a verdict
instead of re-running.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_current_user_id
from app.config import DataSource, settings
from app.domain.models.connection import ConnectionProvider
from app.domain.services.investigation import list_investigations

router = APIRouter(prefix="/customers", tags=["customers"])

STRIPE_API = "https://api.stripe.com/v1"
LOST_STATUSES = ("canceled", "past_due", "incomplete", "unpaid")


class LastInvestigation(BaseModel):
    id: str
    status: str
    primary_cause: str | None = None
    recoverability: str | None = None
    intervention: str | None = None
    completed_at: datetime | None = None


class CustomerSummary(BaseModel):
    id: str
    name: str
    annual_revenue: Decimal | None = None
    currency: str | None = None
    renewal_date: datetime | None = None
    renewal_status: str | None = None  # lost | payment_failed
    owner_name: str | None = None
    source: str  # seed | stripe
    last_investigation: LastInvestigation | None = None


def _seed_customers() -> list[CustomerSummary]:
    from app.domain.models import CauseCategory
    from app.integrations.seed.fixtures import FIXTURES

    return [
        CustomerSummary(
            id=fx.customer.id,
            name=fx.customer.name,
            annual_revenue=fx.customer.annual_revenue,
            currency=fx.customer.currency,
            renewal_date=fx.customer.renewal_date,
            renewal_status="payment_failed" if fx.expected_cause is CauseCategory.PAYMENT else (fx.customer.renewal_status or "lost"),
            owner_name=fx.customer.owner_name,
            source="seed",
        )
        for fx in FIXTURES.values()
    ]


def _arr(sub: dict[str, Any]) -> Decimal | None:
    items = (sub.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    amount = price.get("unit_amount")
    interval = (price.get("recurring") or {}).get("interval")
    if amount is None:
        return None
    if interval == "year":
        return Decimal(amount) / 100
    if interval == "month":
        return Decimal(amount) * 12 / 100
    return None


def _ts(epoch: int | None) -> datetime | None:
    return datetime.fromtimestamp(epoch, tz=UTC) if epoch else None


async def _stripe_customers(api_key: str) -> list[CustomerSummary]:
    import httpx

    rows: dict[str, CustomerSummary] = {}
    async with httpx.AsyncClient(base_url=STRIPE_API, auth=(api_key, ""), timeout=20) as http:
        params: list[tuple[str, str]] = [("status", "all"), ("limit", "100"), ("expand[]", "data.customer")]
        resp = await http.get("/subscriptions", params=params)
        if resp.status_code == 401:
            raise HTTPException(status_code=502, detail="Stripe rejected the stored API key")
        resp.raise_for_status()
        for sub in resp.json().get("data", []):
            if sub.get("status") not in LOST_STATUSES:
                continue
            cust = sub.get("customer") or {}
            if not isinstance(cust, dict) or cust.get("deleted"):
                continue
            meta = cust.get("metadata") or {}
            cid = meta.get("revive_account_id") or cust.get("id")
            if cid in rows:
                continue
            failed = sub["status"] != "canceled"
            rows[cid] = CustomerSummary(
                id=cid,
                name=cust.get("name") or cust.get("email") or cust["id"],
                annual_revenue=_arr(sub),
                currency=(sub.get("currency") or "usd").upper(),
                renewal_date=_ts(sub.get("canceled_at")) or _ts(sub.get("current_period_end")),
                renewal_status="payment_failed" if failed else "lost",
                owner_name=None,
                source="stripe",
            )
    return list(rows.values())


async def _live_customers(user_id: str) -> list[CustomerSummary]:
    from app.domain.services.connection_manager import ConnectionManager

    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="Live mode reads connections from the backend database. Set REVIVE_DATABASE_URL (Postgres) and restart the backend.",
        )
    try:
        creds = await ConnectionManager().get_credentials(user_id, ConnectionProvider.STRIPE)
    except Exception:  # noqa: BLE001 - no DB / no key -> nothing connected
        creds = None
    api_key = (creds or {}).get("api_key") or (creds or {}).get("token")
    if not api_key:
        return []
    return await _stripe_customers(api_key)


@router.get("", response_model=list[CustomerSummary])
async def list_customers(user_id: str = Depends(get_current_user_id)) -> list[CustomerSummary]:
    customers = _seed_customers() if settings.data_source is DataSource.SEED else await _live_customers(user_id)

    latest: dict[str, dict[str, Any]] = {}
    for inv in await list_investigations(user_id, limit=200):  # newest first
        name = (inv.get("customer_name") or "").lower()
        if name and name not in latest:
            latest[name] = inv
    for c in customers:
        inv = latest.get(c.name.lower())
        if inv:
            c.last_investigation = LastInvestigation(
                id=inv["id"], status=inv["status"], primary_cause=inv.get("primary_cause"),
                recoverability=inv.get("recoverability"), intervention=inv.get("intervention"),
                completed_at=inv.get("completed_at"),
            )
    customers.sort(key=lambda c: c.annual_revenue or Decimal(0), reverse=True)
    return customers
