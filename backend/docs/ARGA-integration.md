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

## Verified: Slack twin (free plan)

Confirmed end-to-end against a real Arga Slack twin:

- Free plan limits: **1 twin per run**, **10-minute** session TTL. So provision one twin per run
  (`arga_twin create "<scenario>" slack`) and move quickly.
- `get_twin_run <run_id>` returns per-twin `mcp_url` and `env_vars` (e.g. `SLACK_USER_TOKEN`).
  Save the connection as `{ "base_url": "<mcp_url>", "token": "<SLACK_USER_TOKEN>" }`.
- The Slack twin MCP exposes real tools: `slack_search_messages`, `slack_read_channel`,
  `slack_list_channels`, `slack_send_message`, `slack_read_thread`, ... `SlackLiveProvider` is
  tuned to these.
- **Scope gotcha:** the placeholder twin user token lacks `search:read`, so `slack_search_messages`
  returns `missing_scope`. `SlackLiveProvider.collect_evidence` therefore falls back to
  `slack_list_channels` + `slack_read_channel` and filters messages mentioning the customer -
  which works with the default token and returns the seeded #renewals messages. For full search,
  mint a scoped user token via the twin's OAuth flow.

## Tuning other twins

Stripe / HubSpot twins differ in schema and transport (`backend` twins may expose a REST API
rather than MCP). For each: `McpClient(twin_url, token).list_tool_names()` (if MCP), then set that
provider's `SEARCH_TOOL` / `CREATE_TASK_TOOL` / arg keys / result fields. If a twin is REST-only,
add a small REST adapter implementing the same Protocol methods instead of `McpClient`.

Live evidence carries no `supports` cause tags, so the LLM (not the heuristic) classifies the
cause - keep `REVIVE_USE_LLM=true` and a valid `HF_TOKEN`.

## Reliability story (judging)

Arga also runs **test-runs with judging criteria + evidence tracking**. Pair that with Revive's
own eval harness (`uv run python -m scripts.run_eval`) to demonstrate the Reliability &
Evaluation dimension - deterministic scenarios, evidence-grounded reasoning, action
verification, approval compliance - on a judge's own platform.
