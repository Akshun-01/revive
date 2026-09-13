"""Customer domain model. Normalized across systems.

Vendor-specific IDs (Stripe customer, HubSpot company) live in `external_ids`,
not as first-class fields.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerContext(BaseModel):
    id: str
    name: str

    annual_revenue: Decimal | None = None
    currency: str | None = None

    renewal_date: datetime | None = None
    renewal_status: str | None = None

    owner_id: str | None = None
    owner_name: str | None = None

    # Cross-system identifiers, e.g. {"stripe": "cus_...", "hubspot": "12345"}.
    external_ids: dict[str, str] = Field(default_factory=dict)
