"""SSE streaming: progress events for a run, and for an approval resume."""

from __future__ import annotations

import re

import pytest
from starlette.testclient import TestClient

from app.config import settings


def _null_singletons() -> None:
    from app.agent import graph as g
    from app.persistence import checkpoint as cp
    from app.persistence import db as dbmod

    cp._saver = None
    cp._pool = None
    g._graph = None
    dbmod._engine = None
    dbmod._sessionmaker = None


@pytest.fixture
def client():
    settings.use_llm = False
    settings.database_url = None  # in-memory checkpointer; no DB needed for SSE
    _null_singletons()
    from app.main import app

    with TestClient(app) as c:
        yield c
    _null_singletons()


def _event_names(text: str) -> list[str]:
    names = []
    pending = None
    for line in text.splitlines():
        if line.startswith("event:"):
            pending = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and pending:
            names.append(pending)
            pending = None
    return names


def test_stream_do_not_pursue_completes(client):
    r = client.get("/api/v1/investigations/stream", params={"customer": "Tidewater Systems"})
    assert r.status_code == 200
    names = _event_names(r.text)
    assert names[0] == "investigation_started"
    assert {"customer_resolved", "diagnosis_completed", "recoverability_decided"}.issubset(names)
    assert "action_executed" not in names  # do_not_pursue takes no actions
    assert names[-1] == "investigation_completed"


def test_stream_approval_then_resume(client):
    r = client.get("/api/v1/investigations/stream", params={"customer": "Northwind Robotics"})
    text = r.text
    names = _event_names(text)
    assert "approval_required" in names
    assert names[-1] == "approval_required"

    inv = re.search(r'"id":\s*"(inv_[0-9a-f]+)"', text).group(1)
    r2 = client.get(f"/api/v1/investigations/{inv}/resume-stream", params={"approved": "true"})
    names2 = _event_names(r2.text)
    assert "action_executed" in names2
    assert "action_verified" in names2
    assert names2[-1] == "investigation_completed"
