# Arga Labs Integration (live MCP twins)

Revive's live layer investigates against upstream MCP servers behind provider Protocols.
Instead of real Stripe/HubSpot/Slack dev accounts, point it at **Arga Labs twins** - stateful
clones of those services, seeded with scenario data. Real integration behavior for the demo,
plus Arga's reliability/eval story, with no production credentials. Arga is a judging company,
so this also lands originality.

## How Arga is shaped (verified)

- One **control MCP** at `https://api.argalabs.com/mcp`, auth `Authorization: Bearer <ARGA_API_KEY>`.
- Control tools include `get_twin_catalog`, `create_twin_run`, `get_twin_run` (+ sandbox/test-run
  tools). The `search_*` context tools (search_slack/search_posthog/search_context) require a
  Team plan; the **free tier uses twins**.
- Catalog confirms `stripe`, `hubspot`, and `slack` twins exist (Slack twin exposes MCP at `/mcp`).
- A **twin run** provisions the twins and returns their URLs + credentials + env vars.

## Flow

1. **Provision twins** (spends one Arga session - do this yourself, not from tests):
   ```bash
   cd backend
   uv run python -m scripts.arga_twin catalog        # free: list twin types
   uv run python -m scripts.arga_twin create \
     "Northwind Robotics did not renew: weekly usage down 67%, no payment failure, repeated onboarding complaints" \
     stripe,hubspot,slack
   # note the run_id, then:
   uv run python -m scripts.arga_twin get <run_id>    # twin URLs + credentials + env vars
   ```

2. **Set backend env** (`backend/.env`):
   ```
   REVIVE_DATA_SOURCE=live
   REVIVE_SECRET_KEY=<fernet key>
   REVIVE_DATABASE_URL=postgresql://revive:revive@localhost:5433/revive
   ARGA_API_KEY=<already set>
   ```

3. **Save a connection per provider** with the twin's base_url + token (base_url overrides the
   default hosted MCP endpoint):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/connections \
     -H "Content-Type: application/json" -H "X-User-Id: demo-user" \
     -d '{"provider":"slack","credentials":{"base_url":"<slack twin mcp url>","token":"<twin token>"}}'
   # repeat for "stripe" and "hubspot"
   ```

4. **Run live** and inspect evidence:
   ```bash
   REVIVE_DATA_SOURCE=live uv run python -m scripts.run_live "Northwind Robotics" --user demo-user
   ```

## Tuning (the one manual step)

`app/integrations/mcp/provider.py` uses best-effort tool names + arg names + result field
paths. Each twin mirrors its real service's schema, which differs per provider and per twin
transport (some twins expose MCP, some a REST/`frontend` API). After a twin run:

1. If the twin exposes MCP: `McpClient(twin_url, token).list_tool_names()` to see its tools,
   then set the provider's `SEARCH_TOOL` / `CREATE_TASK_TOOL` / arg keys / result fields to match.
2. If a twin exposes REST only (not MCP), add a small REST adapter for that provider instead of
   `McpClient` (same Protocol methods).

Live evidence carries no `supports` cause tags, so the LLM (not the heuristic) classifies the
cause - keep `REVIVE_USE_LLM=true` and a valid `HF_TOKEN`.

## Reliability story (judging)

Arga also runs **test-runs with judging criteria + evidence tracking**. Pair that with Revive's
own eval harness (`uv run python -m scripts.run_eval`) to demonstrate the Reliability &
Evaluation dimension - deterministic scenarios, evidence-grounded reasoning, action
verification, approval compliance - on a judge's own platform.
