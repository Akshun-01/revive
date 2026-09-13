"""Run the vertical slice against seed customers and print the result.

Usage:
    uv run python -m scripts.run_slice            # all seed scenarios
    uv run python -m scripts.run_slice "Northwind Robotics"
"""

from __future__ import annotations

import asyncio
import sys

from app.domain.services.investigation import (
    resume_investigation,
    run_investigation,
)
from app.integrations.seed.fixtures import FIXTURES


async def _one(query: str) -> None:
    r = await run_investigation(query)
    cust = r["customer"] or {"name": query}
    diag = r["diagnosis"]
    rec = r["recoverability"]
    itv = r["intervention"]
    print(f"\n=== {cust['name']}  [{r['status']}] ===")
    print(f"  revenue_impact : {r['revenue_impact']}")
    print(f"  evidence       : {len(r['evidence'])} items {r['evidence_sources']}")
    if diag:
        pc = diag["primary_cause"]
        print(f"  cause          : {pc['category']} (conf {pc['confidence']}) <- {pc['supporting_evidence_ids']}")
    if rec:
        print(f"  recoverability : {rec['decision']} (conf {rec['confidence']})")
    if itv:
        print(f"  intervention   : {itv['type']} [{itv['priority']}]")
    _print_actions(r)

    if r["status"] == "waiting_for_approval":
        pa = r["pending_action"]
        print(f"  >> approval needed: {pa['type']} - {pa['description']}")
        print("  >> auto-approving (demo) ...")
        r = await resume_investigation(r["id"], approved=True)
        print(f"  resumed -> [{r['status']}]")
        _print_actions(r)

    for w in r["warnings"]:
        print(f"  ! {w}")


def _print_actions(r: dict) -> None:
    for a in r["actions"]:
        ref = (a.get("result") or {}).get("external_reference")
        print(f"  action         : {a['type']} [{a['status']}] ref={ref}")
    for v in r["verification"]:
        print(f"  verify         : {v['action_id']} verified={v['verified']} {v['discrepancies']}")


async def main() -> None:
    queries = sys.argv[1:] or [f.customer.name for f in FIXTURES.values()]
    for q in queries:
        await _one(q)


if __name__ == "__main__":
    asyncio.run(main())
