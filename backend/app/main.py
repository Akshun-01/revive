"""Revive ASGI application boundary.

FastAPI owns HTTP (web client). FastMCP is mounted at /mcp for external AI clients
(Claude / ChatGPT). Both transports call the same application services; no duplicated
business logic. The MCP tool surface is curated (app/mcp/server.py), not generated.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import approvals, connections, health, investigations
from app.config import settings
from app.mcp.server import mcp

# ASGI app for the MCP server (Streamable HTTP). Mounted below at /mcp.
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run the MCP session-manager lifespan, and create app tables when Postgres is set.
    async with mcp_app.lifespan(app):
        if settings.database_url:
            from app.persistence.db import init_models

            await init_models()
        yield


app = FastAPI(
    title="Revive",
    description="AI-powered revenue recovery agent.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for the Next.js frontend. Broad for the hackathon; tighten origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(investigations.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")

# Revive MCP server for external AI clients (Claude / ChatGPT / Cursor).
app.mount("/mcp", mcp_app)
