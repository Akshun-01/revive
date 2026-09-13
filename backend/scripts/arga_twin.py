"""Drive Arga twin provisioning. Manual - `create` consumes an Arga session.

    uv run python -m scripts.arga_twin catalog
    uv run python -m scripts.arga_twin create "Northwind Robotics did not renew: usage down 67%, no payment failure, onboarding complaints" stripe,hubspot,slack
    uv run python -m scripts.arga_twin get <run_id>

After `create`/`get` returns twin URLs + credentials, save one connection per provider with
its base_url + token (POST /api/v1/connections), set REVIVE_DATA_SOURCE=live, then:
    uv run python -m scripts.run_live "Northwind Robotics"
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.config import settings  # noqa: F401 - loads .env (ARGA_API_KEY)
from app.integrations.arga.orchestrator import ArgaOrchestrator


def _show(result) -> None:
    print(json.dumps(result, indent=2, default=str) if not isinstance(result, str) else result)


async def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "catalog"
    arga = ArgaOrchestrator()

    if cmd == "catalog":
        _show(await arga.twin_catalog())
    elif cmd == "create":
        prompt = args[1] if len(args) > 1 else None
        twins = args[2] if len(args) > 2 else "stripe,hubspot,slack"
        # Free plan caps twin sessions at 10 minutes; request that to avoid a plan error.
        ttl = int(args[3]) if len(args) > 3 else 10
        print(f"Creating twin run: twins={twins!r} ttl={ttl}m (consumes an Arga session)\n")
        _show(await arga.create_twin_run(twins, scenario_prompt=prompt, ttl_minutes=ttl))
    elif cmd == "get":
        if len(args) < 2:
            print("usage: arga_twin get <run_id>")
            return
        _show(await arga.get_twin_run(args[1]))
    else:
        print(f"unknown command: {cmd} (use catalog | create | get)")


if __name__ == "__main__":
    asyncio.run(main())
