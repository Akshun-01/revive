"""Recoverability decision + intervention selection."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Recoverability(str, Enum):
    RECOVERABLE = "recoverable"
    NOT_RECOVERABLE = "not_recoverable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RecoverabilityDecision(BaseModel):
    decision: Recoverability
    confidence: float = Field(ge=0.0, le=1.0)

    # Named factors → score, e.g. {"revenue_value": 0.9, "cause_confidence": 0.87}.
    factors: dict[str, float] = Field(default_factory=dict)

    reasoning: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class InterventionType(str, Enum):
    BILLING_INTERVENTION = "billing_intervention"
    TARGETED_ONBOARDING = "targeted_onboarding"
    COMMERCIAL_REVIEW = "commercial_review"
    STAKEHOLDER_REENGAGEMENT = "stakeholder_reengagement"
    SUPPORT_ESCALATION = "support_escalation"
    DO_NOT_PURSUE = "do_not_pursue"


class Intervention(BaseModel):
    type: InterventionType
    priority: Literal["low", "medium", "high"]

    reason: str
    expected_outcome: str
    risk: str

    supporting_evidence_ids: list[str] = Field(default_factory=list)
    approval_required: bool = False
