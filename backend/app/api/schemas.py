"""Request schemas for the REST API. Responses are the service result dicts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
    customer: str = Field(min_length=1, description="Customer name or query, e.g. 'Northwind Robotics'.")


class ResumeRequest(BaseModel):
    approved: bool
    # Optional per-action parameter edits: {action_id: {param: value}}.
    edits: dict[str, dict] | None = None


class ApprovalDecision(BaseModel):
    # Optional edits applied before executing the approved action(s).
    edits: dict[str, dict] | None = None
    reason: str | None = None
