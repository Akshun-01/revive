"""Evaluation harness test: the whole suite must score perfectly in deterministic mode."""

from __future__ import annotations

import pytest

from app.config import settings
from app.evaluation.runner import run_eval


@pytest.fixture(autouse=True)
async def _isolated():
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


async def test_eval_report_perfect():
    report = await run_eval()

    assert report.total == 5
    assert report.cause_accuracy == 1.0
    assert report.recoverability_accuracy == 1.0
    assert report.intervention_accuracy == 1.0
    assert report.revenue_accuracy == 1.0
    assert report.evidence_attribution_accuracy == 1.0
    assert report.verification_success_rate == 1.0
    assert report.approval_compliance == 1.0
    assert report.false_action_rate == 0.0
    assert report.passed is True
