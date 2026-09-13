"""Evidence - first-class domain object. LLM reasons over this, not raw vendor APIs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    STRIPE = "stripe"
    HUBSPOT = "hubspot"
    SLACK = "slack"
    USERLENS = "userlens"


class EvidenceCategory(str, Enum):
    BILLING = "billing"
    PRODUCT_BEHAVIOR = "product_behavior"
    CRM = "crm"
    COMMUNICATION = "communication"


class Evidence(BaseModel):
    id: str

    source: EvidenceSource
    category: EvidenceCategory

    title: str
    finding: str

    # Traceable pointer to the origin, e.g. "slack:msg:abc123".
    source_reference: str | None = None
    timestamp: datetime | None = None

    confidence: float = Field(ge=0.0, le=1.0)

    # Cause categories (as strings) this evidence supports / contradicts.
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
