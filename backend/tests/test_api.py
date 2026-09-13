"""REST + MCP-mount tests via TestClient. Requires Postgres; skips if unreachable.

Exercises the full transport path: POST /investigations -> pause for approval ->
list + approvals -> approve -> completed, plus that the MCP server is mounted at /mcp.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from starlette.testclient import TestClient

from app.config import settings

DB = os.getenv("REVIVE_TEST_DB", "postgresql://revive:revive@127.0.0.1:5433/revive")
HEADERS = {"X-User-Id": "api-user"}


def _null_singletons() -> None:
    # Null (do not dispose) cross-loop singletons so TestClient's loop rebuilds them.
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
    try:
        psycopg.connect(DB, connect_timeout=3).close()
    except Exception as exc:  # noqa: BLE001 - no DB in this environment
        pytest.skip(f"Postgres not available: {exc}")

    settings.use_llm = False
    settings.database_url = DB
    _null_singletons()

    from app.main import app

    with TestClient(app) as c:
        yield c
    _null_singletons()


def test_investigation_flow(client):
    # do_not_pursue: completes immediately, no actions.
    r = client.post("/api/v1/investigations", json={"customer": "Tidewater Systems"}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["intervention"]["type"] == "do_not_pursue"
    assert body["actions"] == []

    # recoverable: pauses for approval of the customer message.
    r = client.post("/api/v1/investigations", json={"customer": "Northwind Robotics"}, headers=HEADERS)
    body = r.json()
    inv = body["id"]
    assert body["status"] == "waiting_for_approval"
    assert body["pending_action"]["type"] == "send_customer_message"

    # list includes it
    listed = client.get("/api/v1/investigations", headers=HEADERS).json()
    assert any(x["id"] == inv for x in listed)

    # approvals surface it
    approvals = client.get("/api/v1/approvals", headers=HEADERS).json()
    assert any(a["investigation_id"] == inv for a in approvals)

    # approve -> resumes, executes, verifies
    r = client.post(f"/api/v1/approvals/{inv}/approve", json={}, headers=HEADERS)
    approved = r.json()
    assert approved["status"] == "completed"
    assert len(approved["actions"]) == 3
    assert all(a["status"] == "verified" for a in approved["actions"])

    # get by id reflects completion
    got = client.get(f"/api/v1/investigations/{inv}", headers=HEADERS).json()
    assert got["status"] == "completed"
    assert got["audit"], "audit trail present"


def test_get_missing_investigation_404(client):
    assert client.get("/api/v1/investigations/inv_does_not_exist", headers=HEADERS).status_code == 404


def test_mcp_server_mounted(client):
    # The MCP endpoint is mounted (a bare GET is not a valid MCP call, but must not 404).
    assert client.get("/mcp").status_code != 404
