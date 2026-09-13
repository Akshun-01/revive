"""Evaluation scenarios - expected outcomes per customer.

Derived from the seed fixtures so scenarios and demo data never drift apart.
The runner (added once the graph exists) executes each and asserts:
cause accuracy, recoverability accuracy, intervention accuracy, revenue impact.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.domain.models import CauseCategory, InterventionType, Recoverability
from app.integrations.seed.fixtures import FIXTURES


class EvaluationScenario(BaseModel):
    name: str
    customer: str
    expected_cause: CauseCategory
    expected_recoverability: Recoverability
    expected_intervention: InterventionType
    expected_revenue_impact: Decimal


def all_scenarios() -> list[EvaluationScenario]:
    return [
        EvaluationScenario(
            name=fx.key,
            customer=fx.customer.name,
            expected_cause=fx.expected_cause,
            expected_recoverability=fx.expected_recoverability,
            expected_intervention=fx.expected_intervention,
            expected_revenue_impact=fx.expected_revenue_impact,
        )
        for fx in FIXTURES.values()
    ]
