"""InvestigationService: runs the graph, shapes the API result, persists the record.

Both REST and Revive-MCP transports call this (added in step 8). The result dict matches
the frontend API contract in backend/docs/API.md.

Two layers of persistence:
  * LangGraph checkpointer  - opaque graph state keyed by thread_id, used for resume.
  * investigations + audit_events tables - queryable application records + investigation
    trace, written here when DATABASE_URL is set. The audit trail is derived from state,
    so the graph nodes stay free of persistence concerns.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.agent.graph import get_graph
from app.agent.state import ReviveState
from app.config import settings
from app.domain.models import ActionStatus, InvestigationStatus

DEFAULT_USER_ID = "demo-user"


def _new_id() -> str:
    return f"inv_{uuid.uuid4().hex[:10]}"


def _build_audit(state: ReviveState) -> list[dict]:
    """Derive an ordered investigation trace from the current state."""
    at = state.get("created_at")
    events: list[dict] = []

    customer = state.get("customer")
    if customer is not None:
        events.append(
            {"event_type": "customer_resolved", "payload": {"id": customer.id, "name": customer.name}, "at": at}
        )
    for source, status in state.get("evidence_sources", {}).items():
        events.append(
            {"event_type": "evidence_source_completed", "payload": {"source": source, "status": status}, "at": at}
        )
    diagnosis = state.get("diagnosis")
    if diagnosis is not None:
        events.append(
            {
                "event_type": "diagnosis_completed",
                "payload": {
                    "primary_cause": diagnosis.primary_cause.category.value,
                    "confidence": diagnosis.primary_cause.confidence,
                },
                "at": at,
            }
        )
    recoverability = state.get("recoverability")
    if recoverability is not None:
        events.append(
            {
                "event_type": "recoverability_decided",
                "payload": {"decision": recoverability.decision.value, "confidence": recoverability.confidence},
                "at": at,
            }
        )
    intervention = state.get("intervention")
    if intervention is not None:
        events.append(
            {"event_type": "intervention_selected", "payload": {"type": intervention.type.value}, "at": at}
        )
    for action in state.get("actions", []):
        if action.approval_required and action.status is ActionStatus.PROPOSED:
            events.append(
                {"event_type": "approval_required", "payload": {"action_id": action.id, "type": action.type.value}, "at": at}
            )
    for result in state.get("action_results", []):
        events.append(
            {
                "event_type": "action_executed",
                "payload": {"action_id": result.action_id, "success": result.success, "ref": result.external_reference},
                "at": result.executed_at.isoformat(),
            }
        )
    for verification in state.get("verification_results", []):
        events.append(
            {
                "event_type": "action_verified",
                "payload": {"action_id": verification.action_id, "verified": verification.verified},
                "at": verification.verified_at.isoformat(),
            }
        )
    return events


def _result(state: ReviveState, inv_id: str) -> dict:
    customer = state.get("customer")
    diagnosis = state.get("diagnosis")
    recoverability = state.get("recoverability")
    intervention = state.get("intervention")
    status = state.get("status", InvestigationStatus.FAILED)

    revenue = None
    if customer and customer.annual_revenue is not None:
        revenue = float(customer.annual_revenue)

    # Embed each action's execution result inline (per the frontend API contract).
    results_by_id = {r.action_id: r for r in state.get("action_results", [])}
    actions = []
    pending_action = None
    for action in state.get("actions", []):
        item = action.model_dump(mode="json")
        result = results_by_id.get(action.id)
        item["result"] = result.model_dump(mode="json") if result else None
        actions.append(item)
        if action.approval_required and result is None:
            pending_action = item

    return {
        "id": inv_id,
        "status": status.value if isinstance(status, InvestigationStatus) else status,
        "customer": customer.model_dump(mode="json") if customer else None,
        "revenue_impact": revenue,
        "evidence": [e.model_dump(mode="json") for e in state.get("evidence", [])],
        "evidence_sources": state.get("evidence_sources", {}),
        "diagnosis": diagnosis.model_dump(mode="json") if diagnosis else None,
        "recoverability": recoverability.model_dump(mode="json") if recoverability else None,
        "intervention": intervention.model_dump(mode="json") if intervention else None,
        "actions": actions,
        "verification": [v.model_dump(mode="json") for v in state.get("verification_results", [])],
        "pending_action": pending_action,
        "audit": _build_audit(state),
        "warnings": state.get("warnings", []),
        "created_at": state.get("created_at"),
        "completed_at": datetime.now(UTC).isoformat(),
    }


async def _snapshot_result(graph, inv_id: str, config: dict) -> dict | None:
    snapshot = await graph.aget_state(config)
    if not snapshot or not snapshot.values:
        return None
    result = _result(snapshot.values, inv_id)
    # snapshot.next non-empty => the graph is paused at an interrupt (awaiting approval).
    if snapshot.next:
        result["status"] = InvestigationStatus.WAITING_FOR_APPROVAL.value
    return result


async def _persist(user_id: str, result: dict | None) -> None:
    """Write the queryable investigation row + audit trail when Postgres is configured."""
    if not settings.database_url or result is None:
        return
    from app.persistence.repositories import AuditRepository, InvestigationRepository

    await InvestigationRepository().upsert(user_id, result)
    await AuditRepository().replace(result["id"], result.get("audit", []))


async def run_investigation(customer_query: str, user_id: str = DEFAULT_USER_ID) -> dict:
    inv_id = _new_id()
    initial: ReviveState = {
        "investigation_id": inv_id,
        "customer_query": customer_query,
        "user_id": user_id,
        "created_at": datetime.now(UTC).isoformat(),
        "evidence": [],
        "evidence_sources": {},
        "actions": [],
        "action_results": [],
        "verification_results": [],
        "warnings": [],
        "status": InvestigationStatus.CREATED,
    }
    graph = await get_graph()
    config = {"configurable": {"thread_id": inv_id}}
    await graph.ainvoke(initial, config)
    result = await _snapshot_result(graph, inv_id, config)
    await _persist(user_id, result)
    return result


async def resume_investigation(
    inv_id: str, approved: bool, edits: dict | None = None, user_id: str = DEFAULT_USER_ID
) -> dict | None:
    """Resume a paused investigation with a human approval decision."""
    from langgraph.types import Command

    graph = await get_graph()
    config = {"configurable": {"thread_id": inv_id}}
    await graph.ainvoke(Command(resume={"approved": approved, "edits": edits or {}}), config)
    result = await _snapshot_result(graph, inv_id, config)
    await _persist(user_id, result)
    return result


async def get_investigation(inv_id: str) -> dict | None:
    """Read a persisted investigation from the checkpointer by id."""
    graph = await get_graph()
    return await _snapshot_result(graph, inv_id, {"configurable": {"thread_id": inv_id}})


def _events_for(node: str, delta: dict) -> list[tuple[str, dict]]:
    """Map a LangGraph node update to SSE (event_type, payload) pairs."""
    out: list[tuple[str, dict]] = []
    if node == "resolve_customer":
        customer = delta.get("customer")
        if customer is not None:
            out.append(("customer_resolved", {"id": customer.id, "name": customer.name}))
    elif node == "collect_evidence":
        out.append(
            (
                "evidence_collected",
                {"sources": delta.get("evidence_sources", {}), "count": len(delta.get("evidence", []))},
            )
        )
    elif node == "diagnose":
        d = delta.get("diagnosis")
        if d:
            out.append(
                ("diagnosis_completed", {"primary_cause": d.primary_cause.category.value, "confidence": d.primary_cause.confidence})
            )
    elif node == "assess_recoverability":
        r = delta.get("recoverability")
        if r:
            out.append(("recoverability_decided", {"decision": r.decision.value, "confidence": r.confidence}))
    elif node == "select_intervention":
        i = delta.get("intervention")
        if i:
            out.append(("intervention_selected", {"type": i.type.value}))
    elif node == "plan_actions":
        out.append(("actions_planned", {"count": len(delta.get("actions", []))}))
    elif node == "execute_actions":
        for res in delta.get("action_results", []):
            out.append(("action_executed", {"action_id": res.action_id, "success": res.success, "ref": res.external_reference}))
    elif node == "verify_actions":
        for v in delta.get("verification_results", []):
            out.append(("action_verified", {"action_id": v.action_id, "verified": v.verified}))
    return out


async def _stream_updates(graph, inv_id: str, config: dict, source):
    """Yield (event_type, payload) as the graph advances, pausing at an approval interrupt."""
    async for chunk in graph.astream(source, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            result = await _snapshot_result(graph, inv_id, config)
            yield "approval_required", {
                "investigation_id": inv_id,
                "pending_action": (result or {}).get("pending_action"),
            }
            return
        for node, delta in chunk.items():
            for event in _events_for(node, delta):
                yield event
    result = await _snapshot_result(graph, inv_id, config)
    yield "investigation_completed", {"status": (result or {}).get("status"), "investigation_id": inv_id}


async def stream_investigation(customer_query: str, user_id: str = DEFAULT_USER_ID):
    """Start an investigation and stream progress events. Ends at completion or approval."""
    inv_id = _new_id()
    initial: ReviveState = {
        "investigation_id": inv_id,
        "customer_query": customer_query,
        "user_id": user_id,
        "created_at": datetime.now(UTC).isoformat(),
        "evidence": [],
        "evidence_sources": {},
        "actions": [],
        "action_results": [],
        "verification_results": [],
        "warnings": [],
        "status": InvestigationStatus.CREATED,
    }
    graph = await get_graph()
    config = {"configurable": {"thread_id": inv_id}}
    yield "investigation_started", {"id": inv_id, "customer_query": customer_query}
    async for event in _stream_updates(graph, inv_id, config, initial):
        yield event
    await _persist(user_id, await _snapshot_result(graph, inv_id, config))


async def stream_resume(inv_id: str, approved: bool, edits: dict | None = None, user_id: str = DEFAULT_USER_ID):
    """Resume a paused investigation and stream the remaining progress events."""
    from langgraph.types import Command

    graph = await get_graph()
    config = {"configurable": {"thread_id": inv_id}}
    source = Command(resume={"approved": approved, "edits": edits or {}})
    async for event in _stream_updates(graph, inv_id, config, source):
        yield event
    await _persist(user_id, await _snapshot_result(graph, inv_id, config))


async def list_investigations(user_id: str = DEFAULT_USER_ID, limit: int = 50) -> list[dict]:
    """List investigation summaries for a user from the application table."""
    if not settings.database_url:
        return []
    from app.persistence.repositories import InvestigationRepository

    return await InvestigationRepository().list(user_id, limit)
