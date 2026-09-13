"""Investigation + audit persistence (Postgres). Skips if the DB is unreachable.

Uses the Postgres checkpointer AND the application tables, so it exercises the full
step-7 persistence path: run -> investigations row + audit_events rows -> list + read.
"""

from __future__ import annotations

import os

import pytest

from app.config import settings

TEST_USER = "persist-user"


@pytest.fixture
async def db():
    from app.agent import graph as g
    from app.persistence import checkpoint as cp
    from app.persistence import db as dbmod

    settings.use_llm = False
    settings.database_url = os.getenv(
        "REVIVE_TEST_DB", "postgresql://revive:revive@127.0.0.1:5433/revive"
    )
    await cp.reset_checkpointer()
    await g.reset_graph()
    await dbmod.reset_db()
    try:
        await dbmod.init_models()
    except Exception as exc:  # noqa: BLE001 - no DB available in this environment
        await dbmod.reset_db()
        pytest.skip(f"Postgres not available: {exc}")
    yield
    await cp.reset_checkpointer()
    await g.reset_graph()
    await dbmod.reset_db()


async def test_investigation_persisted_and_listed(db):
    from app.domain.services.investigation import (
        list_investigations,
        run_investigation,
    )
    from app.persistence.repositories import AuditRepository, InvestigationRepository

    result = await run_investigation("Tidewater Systems", user_id=TEST_USER)
    inv_id = result["id"]

    # investigations row is queryable without replaying the graph
    stored = await InvestigationRepository().get(inv_id)
    assert stored is not None
    assert stored["status"] == "completed"
    assert stored["recoverability"]["decision"] == "not_recoverable"

    # audit trail persisted and ordered
    audit = await AuditRepository().list(inv_id)
    assert audit and audit[0]["seq"] == 0
    assert {e["event_type"] for e in audit} >= {
        "customer_resolved",
        "diagnosis_completed",
        "recoverability_decided",
    }

    # summary listing for the user
    listed = await list_investigations(TEST_USER)
    assert any(row["id"] == inv_id for row in listed)


async def test_recoverable_persists_pending_then_completed(db):
    from app.domain.services.investigation import (
        resume_investigation,
        run_investigation,
    )
    from app.persistence.repositories import InvestigationRepository

    result = await run_investigation("Northwind Robotics", user_id=TEST_USER)
    assert result["status"] == "waiting_for_approval"

    # persisted row reflects the paused state
    stored = await InvestigationRepository().get(result["id"])
    assert stored["status"] == "waiting_for_approval"

    resumed = await resume_investigation(result["id"], approved=True, user_id=TEST_USER)
    assert resumed["status"] == "completed"

    # row updated in place after resume
    stored2 = await InvestigationRepository().get(result["id"])
    assert stored2["status"] == "completed"
    assert all(a["status"] == "verified" for a in stored2["actions"])
