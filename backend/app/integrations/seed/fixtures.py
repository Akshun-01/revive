"""Deterministic demo fixtures for Log0's non-renewal scenarios (PRD section 17).

Log0 (https://log0.in) is the example tenant: the SaaS vendor running Revive to
investigate why its own customers failed to renew. Each fixture below is one of Log0's
lost accounts, bundling the normalized customer + per-source Evidence + the expected
investigation outcome (used by the evaluation harness for the reliability score).

These are the ground truth for a safe, repeatable demo. The `seed` provider reads from
here; live MCP produces the same shape from real APIs.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.models import (
    CauseCategory,
    CustomerContext,
    Evidence,
    EvidenceCategory,
    EvidenceSource,
    InterventionType,
    Recoverability,
)


class ScenarioFixture(BaseModel):
    key: str  # slug, e.g. "northwind"
    customer: CustomerContext
    evidence: list[Evidence] = Field(default_factory=list)

    # Expected outcome, asserted by the eval harness.
    expected_cause: CauseCategory
    expected_recoverability: Recoverability
    expected_intervention: InterventionType
    expected_revenue_impact: Decimal


def _ev(
    id_: str,
    source: EvidenceSource,
    category: EvidenceCategory,
    title: str,
    finding: str,
    confidence: float,
    supports: list[str] | None = None,
    contradicts: list[str] | None = None,
) -> Evidence:
    return Evidence(
        id=id_,
        source=source,
        category=category,
        title=title,
        finding=finding,
        source_reference=f"{source.value}:{id_}",
        timestamp=datetime(2026, 9, 10, 12, 0, 0),
        confidence=confidence,
        supports=supports or [],
        contradicts=contradicts or [],
    )


# Scenario 1: Northwind Robotics, product-value failure -> RECOVER / targeted onboarding
NORTHWIND = ScenarioFixture(
    key="northwind",
    customer=CustomerContext(
        id="northwind",
        name="Northwind Robotics",
        annual_revenue=Decimal(36000),
        currency="USD",
        renewal_date=datetime(2026, 9, 10),
        renewal_status="lost",
        owner_id="u_sarah",
        owner_name="Sarah Chen",
        external_ids={"stripe": "cus_northwind", "hubspot": "hs_northwind"},
    ),
    evidence=[
        _ev("nw_st1", EvidenceSource.STRIPE, EvidenceCategory.BILLING,
            "Subscription ended", "Subscription ended Sept 10. No payment failure detected. $36k ARR lost.",
            0.99, contradicts=[CauseCategory.PAYMENT.value]),
        _ev("nw_hs1", EvidenceSource.HUBSPOT, EvidenceCategory.CRM,
            "Renewal closed-lost", "Enterprise account owned by Sarah. Renewal marked closed-lost, no explicit reason.",
            0.9),
        _ev("nw_ul1", EvidenceSource.USERLENS, EvidenceCategory.PRODUCT_BEHAVIOR,
            "Usage decline 67%", "Weekly product activity declined 67% over the final 45 days. Feature X never adopted.",
            0.92, supports=[CauseCategory.PRODUCT_ADOPTION.value]),
        _ev("nw_sl1", EvidenceSource.SLACK, EvidenceCategory.COMMUNICATION,
            "Onboarding friction", "CSM reported repeated onboarding problems after migration; persisted ~6 weeks.",
            0.91, supports=[CauseCategory.PRODUCT_ADOPTION.value]),
    ],
    expected_cause=CauseCategory.PRODUCT_ADOPTION,
    expected_recoverability=Recoverability.RECOVERABLE,
    expected_intervention=InterventionType.TARGETED_ONBOARDING,
    expected_revenue_impact=Decimal(36000),
)

# Scenario 2: Cascade Freight, payment problem -> RECOVER / billing follow-up
CASCADE = ScenarioFixture(
    key="cascade",
    customer=CustomerContext(
        id="cascade", name="Cascade Freight", annual_revenue=Decimal(18000), currency="USD",
        renewal_date=datetime(2026, 9, 10), renewal_status="lost",
        owner_id="u_mike", owner_name="Mike Alvarez",
        external_ids={"stripe": "cus_cascade", "hubspot": "hs_cascade"},
    ),
    evidence=[
        _ev("cf_st1", EvidenceSource.STRIPE, EvidenceCategory.BILLING,
            "Payment failed", "Renewal invoice failed: card declined. 3 retry attempts failed. $18k ARR at risk.",
            0.97, supports=[CauseCategory.PAYMENT.value]),
        _ev("cf_ul1", EvidenceSource.USERLENS, EvidenceCategory.PRODUCT_BEHAVIOR,
            "Usage healthy", "Product usage steady and healthy through the renewal window.",
            0.9, contradicts=[CauseCategory.PRODUCT_ADOPTION.value]),
        _ev("cf_hs1", EvidenceSource.HUBSPOT, EvidenceCategory.CRM,
            "Wants to continue", "Contact confirmed intent to continue; awaiting a new payment method.",
            0.88, supports=[CauseCategory.PAYMENT.value]),
        _ev("cf_sl1", EvidenceSource.SLACK, EvidenceCategory.COMMUNICATION,
            "No complaints", "No product complaints in internal channels.",
            0.8, contradicts=[CauseCategory.CUSTOMER_SUPPORT.value]),
    ],
    expected_cause=CauseCategory.PAYMENT,
    expected_recoverability=Recoverability.RECOVERABLE,
    expected_intervention=InterventionType.BILLING_INTERVENTION,
    expected_revenue_impact=Decimal(18000),
)

# Scenario 3: Meridian Analytics, pricing objection -> RECOVER: COMMERCIAL / commercial review
MERIDIAN = ScenarioFixture(
    key="meridian",
    customer=CustomerContext(
        id="meridian", name="Meridian Analytics", annual_revenue=Decimal(72000), currency="USD",
        renewal_date=datetime(2026, 9, 10), renewal_status="lost",
        owner_id="u_priya", owner_name="Priya Nair",
        external_ids={"stripe": "cus_meridian", "hubspot": "hs_meridian"},
    ),
    evidence=[
        _ev("md_st1", EvidenceSource.STRIPE, EvidenceCategory.BILLING,
            "Payment healthy", "No payment failures. Subscription ended at renewal. $72k ARR lost.",
            0.95, contradicts=[CauseCategory.PAYMENT.value]),
        _ev("md_ul1", EvidenceSource.USERLENS, EvidenceCategory.PRODUCT_BEHAVIOR,
            "Usage healthy", "Strong, consistent product usage; multiple active seats.",
            0.9, contradicts=[CauseCategory.PRODUCT_ADOPTION.value]),
        _ev("md_sl1", EvidenceSource.SLACK, EvidenceCategory.COMMUNICATION,
            "Pricing objections", "Repeated pricing objections raised; customer flagged budget for renewal cost.",
            0.9, supports=[CauseCategory.PRICING.value]),
        _ev("md_hs1", EvidenceSource.HUBSPOT, EvidenceCategory.CRM,
            "Discount negotiation", "Deal notes show active discount negotiation before close-lost.",
            0.88, supports=[CauseCategory.PRICING.value]),
    ],
    expected_cause=CauseCategory.PRICING,
    expected_recoverability=Recoverability.RECOVERABLE,
    expected_intervention=InterventionType.COMMERCIAL_REVIEW,
    expected_revenue_impact=Decimal(72000),
)

# Scenario 4: Tidewater Systems, poor fit / competitor -> DO NOT PURSUE
TIDEWATER = ScenarioFixture(
    key="tidewater",
    customer=CustomerContext(
        id="tidewater", name="Tidewater Systems", annual_revenue=Decimal(8000), currency="USD",
        renewal_date=datetime(2026, 9, 10), renewal_status="lost",
        owner_id=None, owner_name=None,
        external_ids={"stripe": "cus_tidewater", "hubspot": "hs_tidewater"},
    ),
    evidence=[
        _ev("tw_ul1", EvidenceSource.USERLENS, EvidenceCategory.PRODUCT_BEHAVIOR,
            "Usage near zero", "Product usage near zero for the final 90 days.",
            0.93, supports=[CauseCategory.PRODUCT_FIT.value]),
        _ev("tw_sl1", EvidenceSource.SLACK, EvidenceCategory.COMMUNICATION,
            "Moved to competitor", "Customer stated they moved to a competitor tool.",
            0.9, supports=[CauseCategory.PRODUCT_FIT.value]),
        _ev("tw_hs1", EvidenceSource.HUBSPOT, EvidenceCategory.CRM,
            "No active champion", "No active champion; account owner unassigned.",
            0.85, supports=[CauseCategory.ORGANIZATIONAL_CHANGE.value]),
        _ev("tw_st1", EvidenceSource.STRIPE, EvidenceCategory.BILLING,
            "Low ARR", "$8k ARR. No payment failure.",
            0.95, contradicts=[CauseCategory.PAYMENT.value]),
    ],
    expected_cause=CauseCategory.PRODUCT_FIT,
    expected_recoverability=Recoverability.NOT_RECOVERABLE,
    expected_intervention=InterventionType.DO_NOT_PURSUE,
    expected_revenue_impact=Decimal(8000),
)

# Scenario 5: Solstice Media, mixed signals -> MONITOR / INSUFFICIENT EVIDENCE
SOLSTICE = ScenarioFixture(
    key="solstice",
    customer=CustomerContext(
        id="solstice", name="Solstice Media", annual_revenue=Decimal(25000), currency="USD",
        renewal_date=datetime(2026, 9, 10), renewal_status="lost",
        owner_id="u_alex", owner_name="Alex Romero",
        external_ids={"stripe": "cus_solstice", "hubspot": "hs_solstice"},
    ),
    evidence=[
        _ev("sm_st1", EvidenceSource.STRIPE, EvidenceCategory.BILLING,
            "No payment failure", "No payment failure. Subscription ended. $25k ARR lost.",
            0.9, contradicts=[CauseCategory.PAYMENT.value]),
        _ev("sm_ul1", EvidenceSource.USERLENS, EvidenceCategory.PRODUCT_BEHAVIOR,
            "Mixed usage", "Usage mixed: some features up, others down. No clear trend.",
            0.5),
        _ev("sm_hs1", EvidenceSource.HUBSPOT, EvidenceCategory.CRM,
            "No loss reason", "Renewal closed-lost with no recorded reason. Sparse notes.",
            0.55),
    ],
    expected_cause=CauseCategory.INSUFFICIENT_EVIDENCE,
    expected_recoverability=Recoverability.INSUFFICIENT_EVIDENCE,
    expected_intervention=InterventionType.STAKEHOLDER_REENGAGEMENT,
    expected_revenue_impact=Decimal(25000),
)


FIXTURES: dict[str, ScenarioFixture] = {
    f.key: f for f in (NORTHWIND, CASCADE, MERIDIAN, TIDEWATER, SOLSTICE)
}


def resolve_fixture(query: str) -> ScenarioFixture | None:
    """Match a free-text customer query to a fixture (by key or name substring)."""
    q = query.strip().lower()
    for f in FIXTURES.values():
        if q == f.key or q in f.customer.name.lower():
            return f
    return None
