"""Repositories for application tables (investigations, audit events).

Thin data-access over SQLAlchemy async sessions. Business logic stays in services.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from app.persistence.db import get_sessionmaker
from app.persistence.models import AuditEventRow, InvestigationRow


class InvestigationRepository:
    async def upsert(self, user_id: str, result: dict[str, Any]) -> None:
        customer = result.get("customer") or {}
        diagnosis = result.get("diagnosis") or {}
        primary = (diagnosis.get("primary_cause") or {}).get("category")
        recoverability = (result.get("recoverability") or {}).get("decision")
        intervention = (result.get("intervention") or {}).get("type")

        async with get_sessionmaker()() as session:
            row = await session.get(InvestigationRow, result["id"])
            fields = {
                "user_id": user_id,
                "customer_query": customer.get("name") or result.get("id"),
                "customer_id": customer.get("id"),
                "customer_name": customer.get("name"),
                "status": result["status"],
                "revenue_impact": result.get("revenue_impact"),
                "primary_cause": primary,
                "recoverability": recoverability,
                "intervention": intervention,
                "result": result,
                "created_at": result.get("created_at"),
                "completed_at": result.get("completed_at"),
            }
            if row is None:
                session.add(InvestigationRow(id=result["id"], **fields))
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            await session.commit()

    async def get(self, investigation_id: str) -> dict[str, Any] | None:
        async with get_sessionmaker()() as session:
            row = await session.get(InvestigationRow, investigation_id)
            return row.result if row else None

    async def list(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(
                    select(InvestigationRow)
                    .where(InvestigationRow.user_id == user_id)
                    .order_by(InvestigationRow.updated_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "customer_name": r.customer_name,
                    "status": r.status,
                    "revenue_impact": r.revenue_impact,
                    "primary_cause": r.primary_cause,
                    "recoverability": r.recoverability,
                    "intervention": r.intervention,
                    "created_at": r.created_at,
                    "completed_at": r.completed_at,
                }
                for r in rows
            ]


class AuditRepository:
    async def replace(self, investigation_id: str, events: list[dict[str, Any]]) -> None:
        """Rebuild the audit trail for an investigation (idempotent per persist)."""
        async with get_sessionmaker()() as session:
            await session.execute(
                delete(AuditEventRow).where(AuditEventRow.investigation_id == investigation_id)
            )
            for seq, event in enumerate(events):
                session.add(
                    AuditEventRow(
                        investigation_id=investigation_id,
                        seq=seq,
                        event_type=event["event_type"],
                        payload=event.get("payload", {}),
                        at=event.get("at"),
                    )
                )
            await session.commit()

    async def list(self, investigation_id: str) -> list[dict[str, Any]]:
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(
                    select(AuditEventRow)
                    .where(AuditEventRow.investigation_id == investigation_id)
                    .order_by(AuditEventRow.seq.asc())
                )
            ).scalars().all()
            return [
                {"seq": r.seq, "event_type": r.event_type, "payload": r.payload, "at": r.at}
                for r in rows
            ]
