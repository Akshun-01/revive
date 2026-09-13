"""Dev server entrypoint.

    uv run python -m scripts.serve

Why not `uvicorn app.main:app`? On Windows uvicorn forces a ProactorEventLoop, but psycopg's
async driver (the Postgres checkpointer) requires a SelectorEventLoop. We set the selector
policy first, then run uvicorn with loop="none" so it uses the loop we control.
"""

from __future__ import annotations

import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn


def main() -> None:
    host = os.getenv("REVIVE_HOST", "127.0.0.1")
    port = int(os.getenv("REVIVE_PORT", "8000"))
    config = uvicorn.Config("app.main:app", host=host, port=port, loop="none", log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
