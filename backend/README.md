# Revive Backend

AI-powered revenue-recovery agent for B2B SaaS non-renewals. FastAPI application boundary, a LangGraph investigation workflow, and a FastMCP server, all behind one ASGI app. Both a web
client (REST + SSE) and AI clients (MCP) call the same application services.

Part of the [Revive](../README.md) project. See also: [API contract](docs/API.md) · [Deployment](../docs/DEPLOY.md) · [Arga Labs reliability twins](docs/ARGA-integration.md).

## Highlights

- **Controlled LangGraph workflow**, not a free-form ReAct loop: `resolve -> collect evidence -> normalize -> diagnose -> assess recoverability -> select intervention -> plan -> approve -> execute -> verify -> finalize`.
- **Evidence-first reasoning.** A deterministic heuristic derives the diagnosis from structured evidence; the LLM (HuggingFace) enriches it. If the LLM is unavailable the heuristic stands, so the workflow always completes.
- **Human-in-the-loop.** External and financial actions are classified by a deterministic policy (never the LLM) and pause the graph with a LangGraph `interrupt()`.
- **Act then verify.** Every write is re-read from the source system and compared expected vs actual before it is marked `verified`. Actions are idempotent.
- **Durable and resumable.** Full graph state is persisted in Postgres (LangGraph checkpointer); a paused investigation survives restarts and resumes exactly where it stopped.
- **Two transports, one brain.** REST + SSE for the web app, FastMCP for AI clients, sharing the same services.
- **Provider abstraction.** Vendor details (Stripe, HubSpot, Slack, Userlens) sit behind `Protocol` interfaces with two implementations: deterministic `seed` fixtures and `live` MCP/REST.

## Tech stack

Python 3.13 · FastAPI · FastMCP · LangGraph · LangChain + `langchain-huggingface` · Pydantic v2 · PostgreSQL (SQLAlchemy 2, asyncpg, psycopg) · `cryptography` (Fernet) · Uvicorn · uv · pytest · ruff.

## Project structure

```
backend/
├── app/
│   ├── main.py              # ASGI app: FastAPI + FastMCP mounted at /mcp
│   ├── config.py            # settings (env), event-loop + logging setup
│   ├── api/
│   │   ├── dependencies.py  # stub auth (X-User-Id)
│   │   ├── schemas.py
│   │   └── routes/          # health, investigations (+SSE), approvals, connections, customers
│   ├── mcp/server.py        # Revive MCP server (curated business tools)
│   ├── agent/               # LangGraph: state, nodes, graph, llm, prompts
│   ├── domain/
│   │   ├── models/          # Evidence, Diagnosis, Recovery, Action, Connection, ...
│   │   ├── services/        # investigation + connection_manager
│   │   └── policies/        # deterministic action policy
│   ├── integrations/
│   │   ├── base.py          # provider Protocols
│   │   ├── factory.py       # seed vs live selection
│   │   ├── seed/            # deterministic fixtures (5 scenarios)
│   │   ├── mcp/             # live MCP client + providers
│   │   └── arga/            # Arga Labs twin orchestrator
│   ├── persistence/         # checkpointer, SQLAlchemy engine, models, repositories
│   └── evaluation/          # reliability harness + metrics
├── scripts/                 # serve, run_slice, run_eval, run_live, arga_twin
├── tests/                   # workflow, API, SSE, MCP, persistence, connections, eval
├── docs/                    # API.md, ARGA-integration.md
├── Dockerfile
└── pyproject.toml
```

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python 3.13 and dependencies)
- Docker (for PostgreSQL), or a reachable Postgres instance

### 1. Install

```bash
cd backend
uv sync --extra dev --extra db
```

### 2. Configure

```bash
cp .env.example .env
# generate a Fernet key for encrypting stored connection credentials:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep `.env` values unquoted (Docker Compose passes quotes literally). See the env reference below.

### 3. Postgres

```bash
docker compose up -d postgres   # from repo root; host port 5433
```

### 4. Run

```bash
uv run python -m scripts.serve   # http://127.0.0.1:8000
```

- Swagger UI: `/docs` · ReDoc: `/redoc` · OpenAPI: `/openapi.json`
- Health: `/api/v1/health` · MCP: `/mcp`

> Use `scripts.serve` rather than `uvicorn` directly. On Windows it selects the SelectorEventLoop
> (psycopg's async driver requires it) and enables proxy headers so `/mcp` works behind a TLS proxy.

## Environment variables

| Variable                                      | Default                              | Purpose                                                                       |
| --------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------- |
| `REVIVE_DATA_SOURCE`                        | `seed`                             | `seed` (deterministic fixtures) or `live` (per-user MCP/REST connections) |
| `REVIVE_USE_LLM`                            | `true`                             | Use HuggingFace for diagnosis; heuristic fallback when off/unavailable        |
| `REVIVE_HF_MODEL`                           | `meta-llama/Llama-3.1-8B-Instruct` | LLM model id                                                                  |
| `HF_TOKEN`                                  | (unset)                              | HuggingFace token (read by`huggingface_hub`)                                |
| `REVIVE_DATABASE_URL`                       | (unset)                              | Postgres URL (psycopg format). Blank runs in-memory (no persistence)          |
| `REVIVE_SECRET_KEY`                         | (unset)                              | Fernet key encrypting stored connection credentials (required for`live`)    |
| `REVIVE_TENANT_NAME`                        | `Log0`                             | Tenant name used in prompts and internal notifications                        |
| `ARGA_API_KEY`                              | (unset)                              | Arga Labs control-MCP key (twin orchestration)                                |
| `LANGCHAIN_TRACING_V2`                      | (unset)                              | `true` to enable LangSmith tracing                                          |
| `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` | (unset)                              | LangSmith credentials / project                                               |
| `REVIVE_HOST` / `REVIVE_PORT`             | `127.0.0.1` / `8000`             | Bind address for`scripts.serve`                                             |

Env vars are `REVIVE_`-prefixed except third-party ones read directly (`HF_TOKEN`, `LANGCHAIN_*`, `ARGA_API_KEY`).

## Scripts

```bash
uv run python -m scripts.serve                     # run the API + MCP server
uv run python -m scripts.run_slice "Northwind Robotics"  # run one investigation (seed)
uv run python -m scripts.run_eval                  # reliability report -> eval_report.json
uv run python -m scripts.run_live "Acme Corp"      # run against live connections (REVIVE_DATA_SOURCE=live)
uv run python -m scripts.arga_twin catalog|create|get    # Arga twin orchestration
```

## API

REST base: `/api/v1`. Full contract with request/response shapes: [`docs/API.md`](docs/API.md).

| Method          | Path                                       | Purpose                                                               |
| --------------- | ------------------------------------------ | --------------------------------------------------------------------- |
| GET             | `/health`                                | Liveness, data source, persistence, LLM state                         |
| POST            | `/investigations`                        | Start an investigation (runs synchronously, returns the full result)  |
| GET             | `/investigations`                        | List investigation summaries                                          |
| GET             | `/investigations/{id}`                   | Full investigation                                                    |
| GET             | `/investigations/stream`                 | Start + stream progress (SSE)                                         |
| GET             | `/investigations/{id}/resume-stream`     | Resume + stream (SSE)                                                 |
| POST            | `/investigations/{id}/resume`            | Resume a paused investigation                                         |
| GET             | `/approvals`                             | Pending approvals                                                     |
| POST            | `/approvals/{id}/approve` \| `/reject` | Resolve an approval                                                   |
| GET             | `/customers`                             | Book of business: lost / at-risk renewals (seed, or live from Stripe) |
| GET/POST/DELETE | `/connections`                           | Per-user provider connections (tokens encrypted, never returned)      |
| POST/GET        | `/mcp`                                   | Revive MCP server                                                     |

### MCP tools

Add `http://127.0.0.1:8000/mcp` (or the deployed URL) to any MCP client:

```text
investigate_customer(customer)
get_investigation_result(investigation_id)
list_recent_investigations()
resume_recovery(investigation_id, approved, edits?)
```

## Testing

```bash
uv run pytest -q          # 22 tests: workflow, REST, SSE, MCP, persistence, connections, eval
uv run ruff check app scripts tests
uv run python -m scripts.run_eval   # 8 reliability metrics, all 100% in deterministic mode
```

Tests that need Postgres (persistence, connections, API) skip automatically when it is unreachable.

## Deployment

Containerized (Postgres + backend + Cloudflare tunnel) via the repo-root `docker-compose.yml`.
See [`../docs/DEPLOY.md`](../docs/DEPLOY.md) for the quick tunnel and the stable named-tunnel setup.

```bash
# from repo root
docker compose up -d --build
```
