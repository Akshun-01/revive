"""Investigation routes. Thin transport over InvestigationService.

For the MVP an investigation runs synchronously and the full result is returned (seed is
instant; live is a few seconds). If it pauses for approval, the result carries
status="waiting_for_approval" and `pending_action`; resume with the /resume endpoint.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_current_user_id
from app.api.schemas import InvestigationCreate, ResumeRequest
from app.domain.services.investigation import (
    get_investigation,
    list_investigations,
    resume_investigation,
    run_investigation,
    stream_investigation,
    stream_resume,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _sse(source):
    async def gen():
        async for event_type, data in source:
            yield {"event": event_type, "data": json.dumps(data)}

    return EventSourceResponse(gen())


@router.post("")
async def create_investigation(
    payload: InvestigationCreate, user_id: str = Depends(get_current_user_id)
) -> dict:
    return await run_investigation(payload.customer, user_id=user_id)


@router.get("")
async def list_all(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    return await list_investigations(user_id)


# SSE: start + stream. Declared before /{investigation_id} so "stream" is not captured as an id.
# user_id is a query param because EventSource cannot set headers.
@router.get("/stream")
async def stream_start(customer: str, user_id: str = "demo-user"):
    return _sse(stream_investigation(customer, user_id=user_id))


@router.get("/{investigation_id}/resume-stream")
async def stream_resume_endpoint(
    investigation_id: str, approved: bool = True, user_id: str = "demo-user"
):
    return _sse(stream_resume(investigation_id, approved=approved, user_id=user_id))


@router.get("/{investigation_id}")
async def get_one(investigation_id: str) -> dict:
    result = await get_investigation(investigation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return result


@router.post("/{investigation_id}/resume")
async def resume(
    investigation_id: str,
    payload: ResumeRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    result = await resume_investigation(
        investigation_id, approved=payload.approved, edits=payload.edits, user_id=user_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return result
