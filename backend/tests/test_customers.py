"""GET /customers: seed mode lists the fixtures, sorted by ARR, without a database."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.config import settings


def test_seed_customers_listed(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    from app.main import app

    with TestClient(app) as client:
        res = client.get("/api/v1/customers", headers={"X-User-Id": "t"})
    assert res.status_code == 200
    rows = res.json()
    assert [r["name"] for r in rows][:2] == ["Meridian Analytics", "Northwind Robotics"]
    assert all(r["source"] == "seed" and r["last_investigation"] is None for r in rows)
    assert {r["renewal_status"] for r in rows} <= {"lost", "payment_failed"}
