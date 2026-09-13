"""ConnectionManager: encrypted per-user storage + retrieval of provider credentials.

Credentials are encrypted with Fernet (REVIVE_SECRET_KEY) before hitting the database and
decrypted only inside the backend when building an MCP client. The public API returns
Connection (no secret); only get_credentials returns the decrypted bag, for internal use.
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet
from sqlalchemy import delete, select

from app.config import settings
from app.domain.models.connection import (
    Connection,
    ConnectionCreate,
    ConnectionProvider,
    ConnectionStatus,
)
from app.persistence.db import get_sessionmaker
from app.persistence.models import ConnectionRow


class ConnectionError(Exception):
    pass


def _fernet() -> Fernet:
    if not settings.secret_key:
        raise ConnectionError(
            "REVIVE_SECRET_KEY is not set; cannot encrypt/decrypt connection credentials."
        )
    try:
        return Fernet(settings.secret_key.encode())
    except Exception as exc:
        raise ConnectionError(f"Invalid REVIVE_SECRET_KEY: {exc}") from exc


def _to_public(row: ConnectionRow) -> Connection:
    return Connection(
        id=row.id,
        provider=ConnectionProvider(row.provider),
        status=ConnectionStatus(row.status),
        scopes=row.scopes.split(",") if row.scopes else [],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ConnectionManager:
    async def upsert(self, user_id: str, data: ConnectionCreate) -> Connection:
        token = _fernet().encrypt(json.dumps(data.credentials).encode()).decode()
        scopes = ",".join(data.scopes)
        async with get_sessionmaker()() as session:
            row = (
                await session.execute(
                    select(ConnectionRow).where(
                        ConnectionRow.user_id == user_id,
                        ConnectionRow.provider == data.provider.value,
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                row = ConnectionRow(
                    user_id=user_id,
                    provider=data.provider.value,
                    credentials_encrypted=token,
                    scopes=scopes,
                    status=ConnectionStatus.CONNECTED.value,
                )
                session.add(row)
            else:
                row.credentials_encrypted = token
                row.scopes = scopes
                row.status = ConnectionStatus.CONNECTED.value
            await session.commit()
            await session.refresh(row)
            return _to_public(row)

    async def list(self, user_id: str) -> list[Connection]:
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(
                    select(ConnectionRow).where(ConnectionRow.user_id == user_id)
                )
            ).scalars().all()
            return [_to_public(r) for r in rows]

    async def get_credentials(
        self, user_id: str, provider: ConnectionProvider
    ) -> dict[str, str] | None:
        """Decrypted credential bag for internal use (building an MCP client). Never exposed."""
        async with get_sessionmaker()() as session:
            row = (
                await session.execute(
                    select(ConnectionRow).where(
                        ConnectionRow.user_id == user_id,
                        ConnectionRow.provider == provider.value,
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return json.loads(_fernet().decrypt(row.credentials_encrypted.encode()).decode())

    async def delete(self, user_id: str, provider: ConnectionProvider) -> bool:
        async with get_sessionmaker()() as session:
            result = await session.execute(
                delete(ConnectionRow).where(
                    ConnectionRow.user_id == user_id,
                    ConnectionRow.provider == provider.value,
                )
            )
            await session.commit()
            return result.rowcount > 0
