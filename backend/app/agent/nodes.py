"""Investigation workflow nodes (vertical slice).

Design choice: reasoning is deterministic-first. Each reasoning node computes a
heuristic result from the structured evidence (evidence carries `supports`/`contradicts`
cause tags), then optionally lets the LLM enrich it. If the LLM is unavailable or
returns junk, the heuristic stands. This guarantees the slice always completes and
stays evidence-grounded - directly serving the reliability score.

Kept in one module for slice speed; can be split into nodes/ per LLD later.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.agent.llm import llm_diagnose
from app.agent.state import ReviveState
from app.domain.models import (
    Action,
    ActionResult,
    ActionStatus,
    ActionType,
    CauseCategory,
    CauseHypothesis,
    CustomerContext,
    Diagnosis,
    Evidence,
    Intervention,
    InterventionType,
    InvestigationStatus,
    Recoverability,
    RecoverabilityDecision,
    VerificationResult,
)
from app.domain.policies.action_policy import requires_approval
from app.integrations.factory import get_provider_bundle

# --- static mappings -------------------------------------------------------

_CAUSE_TO_INTERVENTION: dict[CauseCategory, InterventionType] = {
    CauseCategory.PRODUCT_ADOPTION: InterventionType.TARGETED_ONBOARDING,
    CauseCategory.PAYMENT: InterventionType.BILLING_INTERVENTION,
    CauseCategory.PRICING: InterventionType.COMMERCIAL_REVIEW,
    CauseCategory.ORGANIZATIONAL_CHANGE: InterventionType.STAKEHOLDER_REENGAGEMENT,
    CauseCategory.CUSTOMER_SUPPORT: InterventionType.SUPPORT_ESCALATION,
    CauseCategory.PRODUCT_FIT: InterventionType.DO_NOT_PURSUE,
    CauseCategory.INSUFFICIENT_EVIDENCE: InterventionType.STAKEHOLDER_REENGAGEMENT,
    CauseCategory.OTHER: InterventionType.STAKEHOLDER_REENGAGEMENT,
}


# --- resolve_customer ------------------------------------------------------

async def resolve_customer(state: ReviveState) -> ReviveState:
    bundle = await get_provider_bundle(state.get("user_id"))
    query = state["customer_query"]
    data = await bundle.billing.find_customer(query)
    if not data:
        return {
            "customer": None,
            "warnings": [*state.get("warnings", []), f"Customer not found: {query!r}"],
            "status": InvestigationStatus.FAILED,
        }
    return {"customer": CustomerContext.model_validate(data), "status": InvestigationStatus.RUNNING}


# --- collect_evidence (fan-out) -------------------------------------------

async def collect_evidence(state: ReviveState) -> ReviveState:
    customer = state["customer"]
    assert customer is not None
    bundle = await get_provider_bundle(state.get("user_id"))

    sources = {
        "stripe": bundle.billing.collect_evidence(customer.id),
        "hubspot": bundle.crm.collect_evidence(customer.id),
        "slack": bundle.communication.collect_evidence(customer.name),
    }
    if bundle.behavior is not None:
        sources["userlens"] = bundle.behavior.collect_evidence(customer.name)

    results = await asyncio.gather(*sources.values(), return_exceptions=True)

    evidence: list[Evidence] = []
    status_map: dict[str, str] = {}
    warnings = list(state.get("warnings", []))
    for name, res in zip(sources.keys(), results, strict=True):
        if isinstance(res, Exception):
            status_map[name] = f"error: {res}"
            warnings.append(f"{name} evidence unavailable: {res}")
        elif res:
            evidence.extend(res)
            status_map[name] = "ok"
        else:
            status_map[name] = "empty"

    return {"evidence": evidence, "evidence_sources": status_map, "warnings": warnings}


# --- normalize_evidence ----------------------------------------------------

async def normalize_evidence(state: ReviveState) -> ReviveState:
    seen: set[str] = set()
    deduped: list[Evidence] = []
    for e in state.get("evidence", []):
        if e.id in seen:
            continue
        seen.add(e.id)
        e.confidence = max(0.0, min(1.0, e.confidence))  # clamp
        deduped.append(e)
    deduped.sort(key=lambda e: (e.timestamp is None, e.timestamp))
    return {"evidence": deduped}


# --- diagnose --------------------------------------------------------------

def _heuristic_diagnosis(evidence: list[Evidence]) -> Diagnosis:
    weight: dict[str, float] = defaultdict(float)
    support_ids: dict[str, list[str]] = defaultdict(list)
    for e in evidence:
        for cause in e.supports:
            weight[cause] += e.confidence
            support_ids[cause].append(e.id)

    if not weight:
        primary = CauseHypothesis(
            category=CauseCategory.INSUFFICIENT_EVIDENCE,
            confidence=0.3,
            reasoning="No evidence corroborates a specific cause.",
        )
        return Diagnosis(primary_cause=primary, alternatives=[], confidence=0.3)

    ranked = sorted(weight.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(weight.values())
    top_cat, top_w = ranked[0]
    conf = round(min(0.95, top_w / total), 2) if total else 0.3

    contra = [e.id for e in evidence if top_cat in e.contradicts]
    primary = CauseHypothesis(
        category=CauseCategory(top_cat),
        confidence=conf,
        supporting_evidence_ids=support_ids[top_cat],
        contradicting_evidence_ids=contra,
        reasoning=f"Evidence weight favors {top_cat.replace('_', ' ')}.",
    )
    alternatives = [
        CauseHypothesis(
            category=CauseCategory(cat),
            confidence=round(w / total, 2),
            supporting_evidence_ids=support_ids[cat],
            reasoning="Secondary hypothesis from supporting evidence.",
        )
        for cat, w in ranked[1:3]
    ]
    return Diagnosis(primary_cause=primary, alternatives=alternatives, confidence=conf)


async def diagnose(state: ReviveState) -> ReviveState:
    evidence = state.get("evidence", [])
    heuristic = _heuristic_diagnosis(evidence)
    customer = state["customer"]
    name = customer.name if customer else state.get("customer_query", "")

    hint = f"{heuristic.primary_cause.category.value} (conf {heuristic.primary_cause.confidence})"
    # Run blocking LLM call off the event loop; None -> keep heuristic.
    llm_result = await asyncio.to_thread(llm_diagnose, name, evidence, hint)

    diagnosis = llm_result or heuristic
    warnings = list(state.get("warnings", []))
    if llm_result is None:
        warnings.append("Diagnosis produced by deterministic heuristic (LLM unavailable).")
    return {"diagnosis": diagnosis, "warnings": warnings}


# --- assess_recoverability -------------------------------------------------

def _revenue_factor(customer: CustomerContext | None) -> float:
    if customer is None or customer.annual_revenue is None:
        return 0.5
    return round(min(1.0, float(customer.annual_revenue) / 50000.0), 2)


async def assess_recoverability(state: ReviveState) -> ReviveState:
    diagnosis = state["diagnosis"]
    assert diagnosis is not None
    customer = state["customer"]
    cause = diagnosis.primary_cause.category

    if cause is CauseCategory.INSUFFICIENT_EVIDENCE:
        decision, conf = Recoverability.INSUFFICIENT_EVIDENCE, 0.4
        reasoning = "Evidence does not support a confident cause; do not initiate aggressive recovery."
    elif cause is CauseCategory.PRODUCT_FIT:
        decision, conf = Recoverability.NOT_RECOVERABLE, 0.8
        reasoning = "Poor product fit / churned to alternative; recovery not economically rational."
    else:
        decision, conf = Recoverability.RECOVERABLE, diagnosis.primary_cause.confidence
        reasoning = f"Cause ({cause.value}) is controllable and the account warrants a recovery attempt."

    factors = {
        "cause_confidence": diagnosis.primary_cause.confidence,
        "revenue_value": _revenue_factor(customer),
    }
    decision_obj = RecoverabilityDecision(
        decision=decision,
        confidence=conf,
        factors=factors,
        reasoning=reasoning,
        supporting_evidence_ids=diagnosis.primary_cause.supporting_evidence_ids,
    )
    return {"recoverability": decision_obj}


# --- select_intervention ---------------------------------------------------

async def select_intervention(state: ReviveState) -> ReviveState:
    diagnosis = state["diagnosis"]
    recoverability = state["recoverability"]
    assert diagnosis is not None and recoverability is not None
    cause = diagnosis.primary_cause.category

    if recoverability.decision is Recoverability.NOT_RECOVERABLE:
        itype = InterventionType.DO_NOT_PURSUE
        priority = "low"
        reason = "Recovery not rational; close out rather than spend recovery effort."
        expected = "Account remains lost; effort redirected to recoverable customers."
    else:
        itype = _CAUSE_TO_INTERVENTION[cause]
        priority = "high" if recoverability.decision is Recoverability.RECOVERABLE else "medium"
        reason = f"Best-fit intervention for {cause.value.replace('_', ' ')}."
        expected = "Re-engage the account and pursue renewal recovery."

    intervention = Intervention(
        type=itype,
        priority=priority,
        reason=reason,
        expected_outcome=expected,
        risk="Low - internal action." if itype is not InterventionType.DO_NOT_PURSUE else "None.",
        supporting_evidence_ids=diagnosis.primary_cause.supporting_evidence_ids,
        approval_required=False,
    )
    return {"intervention": intervention}


# --- action layer ----------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _action_id() -> str:
    return f"act_{uuid.uuid4().hex[:8]}"


async def plan_actions(state: ReviveState) -> ReviveState:
    """Turn the intervention into concrete actions, gated by the recoverability decision.

    NOT_RECOVERABLE (do_not_pursue): no actions.
    INSUFFICIENT_EVIDENCE: internal Slack flag only (no CRM write, no external outreach).
    RECOVERABLE: HubSpot task + Slack notify + a customer outreach draft (approval-gated).
    """
    intervention = state["intervention"]
    customer = state["customer"]
    recoverability = state["recoverability"]
    assert intervention is not None and customer is not None and recoverability is not None

    if intervention.type is InterventionType.DO_NOT_PURSUE:
        return {"actions": []}

    from app.config import settings

    owner = customer.owner_name or "the account owner"
    label = intervention.type.value.replace("_", " ")
    revenue = f"${customer.annual_revenue:,.0f}" if customer.annual_revenue is not None else "unknown ARR"

    notify = Action(
        id=_action_id(),
        type=ActionType.SEND_INTERNAL_NOTIFICATION,
        description=f"Notify {owner} in Slack about the recovery recommendation.",
        parameters={
            "channel": "#renewals",
            "message": (
                f"[{settings.tenant_name}] {recoverability.decision.value.upper()} for "
                f"{customer.name} ({revenue}): {label}. Owner: {owner}."
            ),
        },
    )

    if recoverability.decision is Recoverability.INSUFFICIENT_EVIDENCE:
        actions = [notify]  # flag for human review only; no CRM write, no customer contact
    else:  # RECOVERABLE
        task = Action(
            id=_action_id(),
            type=ActionType.CREATE_CRM_TASK,
            description=f"Create a HubSpot recovery task for {owner}.",
            parameters={
                "company_id": customer.external_ids.get("hubspot", customer.id),
                "title": f"Recover {customer.name}: {label}",
                "body": intervention.reason,
                "owner_id": customer.owner_id,
            },
        )
        email = Action(
            id=_action_id(),
            type=ActionType.SEND_CUSTOMER_MESSAGE,
            description=f"Send recovery outreach to {customer.name}.",
            parameters={
                "to": f"buyer@{customer.id}.example",
                "subject": f"Let's get {customer.name} back on track",
                "body": (
                    f"Hi,\n\nWe noticed {customer.name} did not renew. Based on our review "
                    f"({label}), we'd like to help resolve it. Can we find 20 minutes this week?\n\n"
                    f"Best,\n{owner}, {settings.tenant_name}"
                ),
            },
        )
        actions = [task, notify, email]

    for a in actions:
        a.approval_required = requires_approval(a)
    return {"actions": actions}


async def approval(state: ReviveState) -> ReviveState:
    """Interrupt for human approval of any approval-required action still proposed.

    Resume payload: {"approved": bool, "edits": {action_id: {param: value}}}.
    On approve, edited params are merged and the action is marked APPROVED for execution;
    on reject it is marked REJECTED and skipped. Durable via the checkpointer.
    """
    from langgraph.types import interrupt

    actions = state.get("actions", [])
    pending = [a for a in actions if a.approval_required and a.status is ActionStatus.PROPOSED]
    if not pending:
        return {}

    decision = interrupt(
        {
            "type": "approval_required",
            "actions": [a.model_dump(mode="json") for a in pending],
        }
    )
    approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
    edits = decision.get("edits", {}) if isinstance(decision, dict) else {}

    for action in pending:
        if approved:
            if action.id in edits:
                action.parameters.update(edits[action.id])
            action.status = ActionStatus.APPROVED
        else:
            action.status = ActionStatus.REJECTED
    return {"actions": actions}


async def execute_actions(state: ReviveState) -> ReviveState:
    """Execute runnable actions: safe internal ones + approved ones. Idempotent."""
    bundle = await get_provider_bundle(state.get("user_id"))
    actions = state.get("actions", [])
    results = list(state.get("action_results", []))
    done = {r.action_id for r in results if r.success}
    warnings = list(state.get("warnings", []))

    for action in actions:
        if action.id in done:  # idempotency guard for retries / resumption
            continue
        safe_internal = not action.approval_required and action.status is ActionStatus.PROPOSED
        runnable = safe_internal or action.status is ActionStatus.APPROVED
        if not runnable:  # approval-required-and-pending, or rejected
            continue
        try:
            if action.type is ActionType.CREATE_CRM_TASK:
                result = await bundle.crm.create_task(
                    action.parameters["company_id"],
                    action.parameters["title"],
                    action.parameters.get("body", ""),
                    action.parameters.get("owner_id"),
                )
            elif action.type is ActionType.SEND_INTERNAL_NOTIFICATION:
                result = await bundle.communication.send_internal_message(
                    action.parameters["channel"], action.parameters["message"]
                )
            elif action.type is ActionType.SEND_CUSTOMER_MESSAGE:
                result = await bundle.communication.send_customer_message(
                    action.parameters["to"], action.parameters.get("body", "")
                )
            else:
                continue
            result.action_id = action.id
            action.status = ActionStatus.EXECUTED if result.success else ActionStatus.FAILED
            results.append(result)
        except Exception as exc:  # noqa: BLE001 - record failure, do not abort the run
            action.status = ActionStatus.FAILED
            results.append(
                ActionResult(action_id=action.id, success=False, message=str(exc), executed_at=_now())
            )
            warnings.append(f"Action {action.type.value} failed: {exc}")

    return {"actions": actions, "action_results": results, "warnings": warnings}


async def verify_actions(state: ReviveState) -> ReviveState:
    """Read each executed action back from its provider and compare expected vs actual."""
    bundle = await get_provider_bundle(state.get("user_id"))
    actions = state.get("actions", [])
    results = state.get("action_results", [])
    by_id = {a.id: a for a in actions}
    verifications = list(state.get("verification_results", []))
    verified_ids = {v.action_id for v in verifications}

    for result in results:
        if not result.success or result.action_id in verified_ids:
            continue
        action = by_id.get(result.action_id)
        if action is None:
            continue

        expected: dict = {}
        actual: dict = {}
        discrepancies: list[str] = []

        if action.type is ActionType.CREATE_CRM_TASK:
            expected = {"title": action.parameters["title"], "owner_id": action.parameters.get("owner_id")}
            task = await bundle.crm.get_task(result.external_reference or "")
            if task:
                actual = {"title": task.get("title"), "owner_id": task.get("owner_id")}
            else:
                discrepancies.append("task not found on read-back")
        elif action.type is ActionType.SEND_INTERNAL_NOTIFICATION:
            expected = {"channel": action.parameters["channel"]}
            message = await bundle.communication.get_message(result.external_reference or "")
            if message:
                actual = {"channel": message.get("channel")}
            else:
                discrepancies.append("message not found on read-back")
        elif action.type is ActionType.SEND_CUSTOMER_MESSAGE:
            expected = {"to": action.parameters["to"]}
            message = await bundle.communication.get_customer_message(result.external_reference or "")
            if message:
                actual = {"to": message.get("to")}
            else:
                discrepancies.append("customer message not found on read-back")

        for key, want in expected.items():
            if actual.get(key) != want:
                discrepancies.append(f"{key}: expected {want!r}, got {actual.get(key)!r}")

        verified = bool(actual) and not discrepancies
        if verified:
            action.status = ActionStatus.VERIFIED
        verifications.append(
            VerificationResult(
                action_id=result.action_id,
                verified=verified,
                expected_state=expected,
                actual_state=actual,
                discrepancies=discrepancies,
                verified_at=_now(),
            )
        )

    return {"actions": actions, "verification_results": verifications}


async def finalize(state: ReviveState) -> ReviveState:
    return {"status": InvestigationStatus.COMPLETED}
