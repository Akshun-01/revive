"""Cause diagnosis models. Every conclusion references evidence IDs."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CauseCategory(str, Enum):
    PRODUCT_ADOPTION = "product_adoption"
    PRICING = "pricing"
    PAYMENT = "payment"
    ORGANIZATIONAL_CHANGE = "organizational_change"
    CUSTOMER_SUPPORT = "customer_support"
    PRODUCT_FIT = "product_fit"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OTHER = "other"


class CauseHypothesis(BaseModel):
    category: CauseCategory
    confidence: float = Field(ge=0.0, le=1.0)

    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)

    reasoning: str


class Diagnosis(BaseModel):
    primary_cause: CauseHypothesis
    alternatives: list[CauseHypothesis] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0)
