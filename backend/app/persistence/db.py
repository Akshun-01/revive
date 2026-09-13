"""Async SQLAlchemy engine + session for application tables (connections, etc.).

Separate from the LangGraph checkpointer (which uses psycopg directly). SQLAlchemy uses
the asyncpg driver, so the psycopg-format DATABASE_URL is rewritten to the asyncpg URL.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _async_url() -> str:
    url = settings.database_url or ""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine = create_async_engine(_async_url(), pool_size=5, future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def init_models() -> None:
    """Create application tables if absent. Called on startup when DATABASE_URL is set."""
    from app.persistence import models  # noqa: F401 - register tables on Base.metadata

    get_sessionmaker()  # ensure engine
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_db() -> None:
    """Dispose the engine. Used by tests for isolation."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
