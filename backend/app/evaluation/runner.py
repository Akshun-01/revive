"""Evaluation runner: run each scenario end-to-end and score it.

Runs the real workflow (same services as REST/MCP). Approval-gated scenarios are checked
for compliance (the customer-facing action must NOT execute before approval), then approved
so the full act -> verify loop is measured.
"""

from __future__ import annotations

from app.domain.services.investigation import resume_investigation, run_investigation
from app.evaluation.metrics import EvalReport, ScenarioResult, build_report
from app.evaluation.scenarios import EvaluationScenario, all_scenarios


async def evaluate_scenario(scenario: EvaluationScenario) -> ScenarioResult:
    result = await run_investigation(scenario.customer, user_id="eval")

    # Approval compliance: any approval-required action must be un-executed at the gate.
    approval_respected = all(
        a["result"] is None for a in result["actions"] if a["approval_required"]
    )
    if result["status"] == "waiting_for_approval":
        result = await resume_investigation(result["id"], approved=True, user_id="eval")

    primary = result["diagnosis"]["primary_cause"]
    cause_ok = primary["category"] == scenario.expected_cause.value
    recoverability_ok = result["recoverability"]["decision"] == scenario.expected_recoverability.value
    intervention_ok = result["intervention"]["type"] == scenario.expected_intervention.value
    revenue_ok = result["revenue_impact"] == float(scenario.expected_revenue_impact)

    evidence_ids = {e["id"] for e in result["evidence"]}
    if primary["category"] == "insufficient_evidence":
        evidence_grounded = True  # correctly declined to ground a cause
    else:
        supporting = primary["supporting_evidence_ids"]
        evidence_grounded = bool(supporting) and set(supporting).issubset(evidence_ids)

    executed = [a for a in result["actions"] if a["result"] and a["result"]["success"]]
    verified = sum(1 for a in result["actions"] if a["status"] == "verified")

    # False action: any execution on a do-not-pursue outcome.
    false_actions = len(executed) if scenario.expected_intervention.value == "do_not_pursue" else 0

    return ScenarioResult(
        name=scenario.name,
        customer=scenario.customer,
        cause_ok=cause_ok,
        recoverability_ok=recoverability_ok,
        intervention_ok=intervention_ok,
        revenue_ok=revenue_ok,
        evidence_grounded=evidence_grounded,
        approval_respected=approval_respected,
        actions_executed=len(executed),
        actions_verified=verified,
        false_actions=false_actions,
        expected={
            "cause": scenario.expected_cause.value,
            "recoverability": scenario.expected_recoverability.value,
            "intervention": scenario.expected_intervention.value,
            "revenue_impact": float(scenario.expected_revenue_impact),
        },
        actual={
            "cause": primary["category"],
            "recoverability": result["recoverability"]["decision"],
            "intervention": result["intervention"]["type"],
            "revenue_impact": result["revenue_impact"],
        },
    )


async def run_eval(scenarios: list[EvaluationScenario] | None = None) -> EvalReport:
    scenarios = scenarios or all_scenarios()
    results = [await evaluate_scenario(s) for s in scenarios]
    return build_report(results)
