"""ConnectionManager tests: encrypted round-trip, upsert, list, delete.

Requires Postgres (docker compose up). Skips if unreachable so the suite still runs offline.
"""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete

from app.config import settings
from app.domain.models.connection import ConnectionCreate, ConnectionProvider
from app.domain.services.connection_manager import ConnectionManager

TEST_USER = "test-user"


@pytest.fixture
async def db():
    from app.persistence import db as dbmod
    from app.persistence.models import ConnectionRow

    settings.database_url = os.getenv(
        "REVIVE_TEST_DB", "postgresql://revive:revive@127.0.0.1:5433/revive"
    )
    settings.secret_key = Fernet.generate_key().decode()
    await dbmod.reset_db()
    try:
        await dbmod.init_models()
    except Exception as exc:  # noqa: BLE001 - no DB available in this environment
        await dbmod.reset_db()
        pytest.skip(f"Postgres not available: {exc}")

    async with dbmod.get_sessionmaker()() as s:
        await s.execute(delete(ConnectionRow).where(ConnectionRow.user_id == TEST_USER))
        await s.commit()

    yield

    async with dbmod.get_sessionmaker()() as s:
        await s.execute(delete(ConnectionRow).where(ConnectionRow.user_id == TEST_USER))
        await s.commit()
    await dbmod.reset_db()


async def test_connection_roundtrip(db):
    mgr = ConnectionManager()

    created = await mgr.upsert(
        TEST_USER,
        ConnectionCreate(
            provider=ConnectionProvider.STRIPE,
            credentials={"api_key": "sk_test_123"},
            scopes=["read"],
        ),
    )
    assert created.provider is ConnectionProvider.STRIPE
    assert created.status.value == "connected"
    # public view must never leak the secret
    assert "sk_test" not in created.model_dump_json()

    assert len(await mgr.list(TEST_USER)) == 1
    assert await mgr.get_credentials(TEST_USER, ConnectionProvider.STRIPE) == {"api_key": "sk_test_123"}

    # upsert updates in place, no duplicate
    await mgr.upsert(
        TEST_USER,
        ConnectionCreate(provider=ConnectionProvider.STRIPE, credentials={"api_key": "sk_test_999"}),
    )
    assert await mgr.get_credentials(TEST_USER, ConnectionProvider.STRIPE) == {"api_key": "sk_test_999"}
    assert len(await mgr.list(TEST_USER)) == 1

    assert await mgr.delete(TEST_USER, ConnectionProvider.STRIPE) is True
    assert await mgr.list(TEST_USER) == []


async def test_credentials_encrypted_at_rest(db):
    from sqlalchemy import select

    from app.persistence import db as dbmod
    from app.persistence.models import ConnectionRow

    mgr = ConnectionManager()
    await mgr.upsert(
        TEST_USER,
        ConnectionCreate(provider=ConnectionProvider.SLACK, credentials={"token": "xoxb-secret"}),
    )
    async with dbmod.get_sessionmaker()() as s:
        row = (
            await s.execute(select(ConnectionRow).where(ConnectionRow.user_id == TEST_USER))
        ).scalar_one()
        # stored blob must not contain the plaintext token
        assert "xoxb-secret" not in row.credentials_encrypted
