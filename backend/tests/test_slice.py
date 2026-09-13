"""Vertical-slice evaluation: run each seed scenario, assert expected outcome.

Forces heuristic mode (use_llm=False) so the test is deterministic and offline.
This is the seed of the reliability-eval harness (build step 9).
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.domain.services.investigation import resume_investigation, run_investigation
from app.evaluation.scenarios import all_scenarios


@pytest.fixture(autouse=True)
async def _isolated():
    """Force heuristic + in-memory checkpointer, isolated from any real .env DATABASE_URL."""
    from app.agent import graph
    from app.persistence import checkpoint

    orig_llm, orig_db = settings.use_llm, settings.database_url
    settings.use_llm = False
    settings.database_url = None
    await checkpoint.reset_checkpointer()
    await graph.reset_graph()
    yield
    settings.use_llm, settings.database_url = orig_llm, orig_db
    await checkpoint.reset_checkpointer()
    await graph.reset_graph()


@pytest.mark.parametrize("scenario", all_scenarios(), ids=lambda s: s.name)
async def test_scenario_outcome(scenario):
    result = await run_investigation(scenario.customer)

    assert result["diagnosis"]["primary_cause"]["category"] == scenario.expected_cause.value
    assert result["recoverability"]["decision"] == scenario.expected_recoverability.value
    assert result["intervention"]["type"] == scenario.expected_intervention.value
    assert result["revenue_impact"] == float(scenario.expected_revenue_impact)

    # Audit trail present and ordered through the core steps.
    types = [e["event_type"] for e in result["audit"]]
    assert "customer_resolved" in types
    assert "diagnosis_completed" in types
    assert "recoverability_decided" in types

    # Evidence grounding: primary cause must cite real evidence ids (except when insufficient).
    pc = result["diagnosis"]["primary_cause"]
    if pc["category"] != "insufficient_evidence":
        ids = {e["id"] for e in result["evidence"]}
        assert set(pc["supporting_evidence_ids"]).issubset(ids)
        assert pc["supporting_evidence_ids"]

    decision = result["recoverability"]["decision"]

    if decision == "not_recoverable":
        # do_not_pursue: no actions, run completes straight away.
        assert result["status"] == "completed"
        assert result["actions"] == []
        assert result["verification"] == []
        return

    if decision == "insufficient_evidence":
        # Internal Slack flag only; no approval gate, completes directly.
        assert result["status"] == "completed"
        assert [a["type"] for a in result["actions"]] == ["send_internal_notification"]
        assert all(a["status"] == "verified" for a in result["actions"])
        return

    # Recoverable: a customer-message action is approval-gated -> paused for approval.
    assert result["status"] == "waiting_for_approval"
    pending = result["pending_action"]
    assert pending is not None and pending["type"] == "send_customer_message"

    # Human approves -> resume -> everything executes and verifies.
    resumed = await resume_investigation(result["id"], approved=True)
    assert resumed["status"] == "completed"
    assert len(resumed["actions"]) == 3
    for action in resumed["actions"]:
        assert action["status"] == "verified"
        assert action["result"]["success"] is True
    assert resumed["verification"] and all(v["verified"] for v in resumed["verification"])


@pytest.mark.parametrize("scenario", [s for s in all_scenarios() if s.expected_recoverability.value == "recoverable"][:1], ids=lambda s: s.name)
async def test_rejection_skips_customer_message(scenario):
    result = await run_investigation(scenario.customer)
    assert result["status"] == "waiting_for_approval"

    resumed = await resume_investigation(result["id"], approved=False)
    assert resumed["status"] == "completed"
    # Rejected customer message never executes; internal actions still verified.
    email = next(a for a in resumed["actions"] if a["type"] == "send_customer_message")
    assert email["status"] == "rejected"
    assert email["result"] is None
