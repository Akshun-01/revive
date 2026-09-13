"""Evaluation metrics: per-scenario results + aggregate reliability report.

Dimensions (PRD section 21 / HLD section 24):
  cause accuracy, recoverability accuracy, intervention accuracy, revenue accuracy,
  evidence attribution, verification success rate, approval compliance, false-action rate.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ScenarioResult(BaseModel):
    name: str
    customer: str

    cause_ok: bool
    recoverability_ok: bool
    intervention_ok: bool
    revenue_ok: bool
    evidence_grounded: bool
    approval_respected: bool

    actions_executed: int
    actions_verified: int
    false_actions: int

    expected: dict[str, Any]
    actual: dict[str, Any]


class EvalReport(BaseModel):
    scenarios: list[ScenarioResult]
    total: int

    cause_accuracy: float
    recoverability_accuracy: float
    intervention_accuracy: float
    revenue_accuracy: float
    evidence_attribution_accuracy: float
    verification_success_rate: float
    approval_compliance: float
    false_action_rate: float

    passed: bool


def build_report(results: list[ScenarioResult]) -> EvalReport:
    n = len(results)

    def rate(predicate) -> float:
        return round(sum(1 for r in results if predicate(r)) / n, 3) if n else 0.0

    total_executed = sum(r.actions_executed for r in results)
    total_verified = sum(r.actions_verified for r in results)
    total_false = sum(r.false_actions for r in results)

    cause = rate(lambda r: r.cause_ok)
    recoverability = rate(lambda r: r.recoverability_ok)
    intervention = rate(lambda r: r.intervention_ok)
    revenue = rate(lambda r: r.revenue_ok)
    evidence = rate(lambda r: r.evidence_grounded)
    approval = rate(lambda r: r.approval_respected)
    verification_rate = round(total_verified / total_executed, 3) if total_executed else 1.0
    false_rate = round(total_false / total_executed, 3) if total_executed else 0.0

    passed = (
        cause == 1.0
        and recoverability == 1.0
        and intervention == 1.0
        and revenue == 1.0
        and evidence == 1.0
        and verification_rate == 1.0
        and approval == 1.0
        and false_rate == 0.0
    )

    return EvalReport(
        scenarios=results,
        total=n,
        cause_accuracy=cause,
        recoverability_accuracy=recoverability,
        intervention_accuracy=intervention,
        revenue_accuracy=revenue,
        evidence_attribution_accuracy=evidence,
        verification_success_rate=verification_rate,
        approval_compliance=approval,
        false_action_rate=false_rate,
        passed=passed,
    )
