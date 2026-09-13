"""Approval routes. Convenience layer over investigation resume.

An approval is identified by its investigation_id (one pending action gate per paused
investigation in the MVP). Approve/reject both resume the workflow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user_id
from app.api.schemas import ApprovalDecision
from app.domain.services.investigation import (
    get_investigation,
    list_investigations,
    resume_investigation,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
async def list_pending(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    pending = []
    for row in await list_investigations(user_id):
        if row["status"] != "waiting_for_approval":
            continue
        full = await get_investigation(row["id"])
        if full and full.get("pending_action"):
            pending.append(
                {
                    "investigation_id": row["id"],
                    "customer": row.get("customer_name"),
                    "pending_action": full["pending_action"],
                }
            )
    return pending


@router.post("/{investigation_id}/approve")
async def approve(
    investigation_id: str,
    decision: ApprovalDecision | None = None,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    edits = decision.edits if decision else None
    result = await resume_investigation(
        investigation_id, approved=True, edits=edits, user_id=user_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return result


@router.post("/{investigation_id}/reject")
async def reject(
    investigation_id: str,
    decision: ApprovalDecision | None = None,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    result = await resume_investigation(investigation_id, approved=False, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return result
