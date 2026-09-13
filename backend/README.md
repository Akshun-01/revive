# Revive Backend

FastAPI (web client) + FastMCP (MCP server) over one ASGI app. Both transports call the same
application services → LangGraph investigation workflow → provider layer.

See root `PRD.md`, `HLD.md`, `LLD.md` for full spec.

## Layout

```
app/
├── main.py            # ASGI app: FastAPI + FastMCP mounted at /mcp
├── config.py          # settings (provider mode, LLM provider, MCP urls)
├── api/routes/        # REST transport (health now; investigations/approvals later)
├── mcp/               # FastMCP tools (added when transports wired)
├── agent/             # LangGraph state + nodes (vertical slice, step 4)
├── domain/
│   ├── models/        # pure Pydantic domain models (evidence, diagnosis, recovery, action)
│   └── services/      # application services (added step 8)
├── integrations/
│   ├── base.py        # provider Protocols (Billing / CRM / Communication)
│   └── seed/          # deterministic fixtures - powers eval + safe demo
└── evaluation/        # scenario harness (reliability score)
```

## Two independent axes

- **Client transport** - REST (`/api/v1/*`) or Revive-MCP (`/mcp`). Both call the same
  services. Upstream data fetch is identical either way.
- **Data source** (`REVIVE_DATA_SOURCE`) - where evidence comes from:
  - **seed** - deterministic fixtures (5 PRD scenarios). Powers eval + demo safety.
  - **live** - live upstream Stripe / HubSpot / Slack MCP. Uses `*_MCP_URL` envs.

Stripe/HubSpot/Slack MCP are the data source for `live` regardless of client transport.
Graph depends on provider Protocols, not vendors. LLM reasoning via `langchain-huggingface`.

## Persistence

Postgres backs the LangGraph checkpointer, so full investigation state (evidence,
diagnosis, recoverability, intervention) is durable and readable across processes and
restarts, keyed by investigation id. Blank `REVIVE_DATABASE_URL` falls back to in-memory.

```bash
docker compose up -d          # from repo root; Postgres on host port 5433
# .env: REVIVE_DATABASE_URL=postgresql://revive:revive@localhost:5433/revive
```

Note: env vars are REVIVE_-prefixed (e.g. `REVIVE_DATABASE_URL`). Host 5433 avoids a
local Postgres already on 5432. On Windows the app selects the SelectorEventLoop, which
psycopg's async driver requires.

## Dev

```bash
cd backend
uv sync --extra dev --extra db
uv run uvicorn app.main:app --reload
# health: GET http://127.0.0.1:8000/api/v1/health

# vertical slice against seed data:
uv run python -m scripts.run_slice
# 5-scenario eval:
uv run pytest -q
```
