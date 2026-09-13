"""Run an investigation in LIVE mode against connected MCP servers (e.g. Arga twins).

Prereqs: Postgres up, REVIVE_SECRET_KEY set, and connections saved for the user with each
provider's twin base_url + token (POST /api/v1/connections). Then:

    REVIVE_DATA_SOURCE=live uv run python -m scripts.run_live "Some Customer" --user demo-user

Prints resolved evidence per source so you can tune tool names/field mappings in
app/integrations/mcp/provider.py against the real twin schemas.
"""

from __future__ import annotations

import asyncio
import sys

from app.config import DataSource, settings
from app.domain.services.investigation import resume_investigation, run_investigation


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    user = "demo-user"
    for i, a in enumerate(sys.argv):
        if a == "--user" and i + 1 < len(sys.argv):
            user = sys.argv[i + 1]
    customer = args[0] if args else "Northwind Robotics"

    if settings.data_source is not DataSource.LIVE:
        print("WARNING: REVIVE_DATA_SOURCE is not 'live'; set it to hit real MCP servers.\n")

    result = await run_investigation(customer, user_id=user)
    print(f"=== {customer} [{result['status']}] (user={user}) ===")
    print(f"evidence sources : {result['evidence_sources']}")
    for e in result["evidence"]:
        print(f"  [{e['source']}] {e['finding'][:120]}")
    if result["status"] == "waiting_for_approval":
        print(f"pending approval : {result['pending_action']['type']} (auto-approving)")
        result = await resume_investigation(result["id"], approved=True, user_id=user)
    diag = result.get("diagnosis") or {}
    print(f"cause            : {(diag.get('primary_cause') or {}).get('category')}")
    print(f"recoverability   : {(result.get('recoverability') or {}).get('decision')}")
    for w in result["warnings"]:
        print(f"  ! {w}")


if __name__ == "__main__":
    asyncio.run(main())
