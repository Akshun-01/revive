"""LangGraph state for the investigation workflow.

Flow: resolve -> collect -> normalize -> diagnose -> recoverability -> intervention
-> plan_actions -> execute_actions -> verify_actions -> finalize. Human approval
(interrupt on approval-required actions) lands in step 6.

Nodes run sequentially (collect fans out internally with asyncio.gather), so plain
TypedDict fields need no concurrent-write reducers. State holds domain model instances;
the in-memory checkpointer serializes them fine.
"""

from __future__ import annotations

from typing import TypedDict

from app.domain.models import (
    Action,
    ActionResult,
    CustomerContext,
    Diagnosis,
    Evidence,
    Intervention,
    InvestigationStatus,
    RecoverabilityDecision,
    VerificationResult,
)


class ReviveState(TypedDict, total=False):
    investigation_id: str
    customer_query: str
    created_at: str
    user_id: str  # whose connections to use in live mode; ignored by the seed provider

    customer: CustomerContext | None

    evidence: list[Evidence]
    evidence_sources: dict[str, str]  # source -> "ok" | "empty" | "error: ..."

    diagnosis: Diagnosis | None
    recoverability: RecoverabilityDecision | None
    intervention: Intervention | None

    actions: list[Action]
    action_results: list[ActionResult]
    verification_results: list[VerificationResult]

    warnings: list[str]
    status: InvestigationStatus
