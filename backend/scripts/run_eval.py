"""Run the evaluation harness, print the reliability report, write eval_report.json.

    uv run python -m scripts.run_eval
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.evaluation.runner import run_eval


def _fmt_pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


async def main() -> None:
    report = await run_eval()

    print("\nRevive Evaluation Report")
    print("=" * 68)
    header = f"{'scenario':<20} {'cause':<7} {'recov':<7} {'interv':<7} {'evid':<6} {'appr':<6}"
    print(header)
    print("-" * 68)
    for s in report.scenarios:
        print(
            f"{s.customer:<20} "
            f"{'ok' if s.cause_ok else 'X':<7} "
            f"{'ok' if s.recoverability_ok else 'X':<7} "
            f"{'ok' if s.intervention_ok else 'X':<7} "
            f"{'ok' if s.evidence_grounded else 'X':<6} "
            f"{'ok' if s.approval_respected else 'X':<6}"
        )
    print("-" * 68)
    print(f"scenarios                 : {report.total}")
    print(f"cause accuracy            : {_fmt_pct(report.cause_accuracy)}")
    print(f"recoverability accuracy   : {_fmt_pct(report.recoverability_accuracy)}")
    print(f"intervention accuracy     : {_fmt_pct(report.intervention_accuracy)}")
    print(f"revenue accuracy          : {_fmt_pct(report.revenue_accuracy)}")
    print(f"evidence attribution      : {_fmt_pct(report.evidence_attribution_accuracy)}")
    print(f"verification success rate : {_fmt_pct(report.verification_success_rate)}")
    print(f"approval compliance       : {_fmt_pct(report.approval_compliance)}")
    print(f"false-action rate         : {_fmt_pct(report.false_action_rate)}")
    print("=" * 68)
    print(f"RESULT: {'PASS' if report.passed else 'FAIL'}")

    out = Path("eval_report.json")
    out.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    print(f"\nWrote {out.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
