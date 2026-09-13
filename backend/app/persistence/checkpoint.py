"""LangGraph checkpointer selection.

DATABASE_URL set  -> AsyncPostgresSaver over a psycopg async pool (durable state).
DATABASE_URL blank -> MemorySaver (in-memory, for tests and no-infra runs).

The saver is a process-wide singleton; the graph is compiled against it once. The full
investigation state (evidence, diagnosis, recoverability, intervention, ...) is persisted
per thread_id (= investigation_id), so a restart or a later read recovers everything.
"""

from __future__ import annotations

import asyncio

from app.config import settings

_saver = None
_pool = None
_lock = asyncio.Lock()


async def get_checkpointer():
    global _saver, _pool
    async with _lock:
        if _saver is not None:
            return _saver

        if not settings.database_url:
            from langgraph.checkpoint.memory import MemorySaver

            _saver = MemorySaver()
            return _saver

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        _pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        await _pool.open()
        # allow our own Pydantic domain models to round-trip through msgpack. Safe here:
        # we control the database and only Revive's own types are ever stored.
        serde = JsonPlusSerializer(allowed_msgpack_modules=True)
        _saver = AsyncPostgresSaver(_pool, serde=serde)
        await _saver.setup()  # idempotent: creates checkpoint tables if absent
        return _saver


async def reset_checkpointer() -> None:
    """Drop the cached saver and close the pool. Used by tests for isolation."""
    global _saver, _pool
    if _pool is not None:
        await _pool.close()
    _saver = None
    _pool = None
