"""Action / approval / verification models + investigation lifecycle enums.

Every side effect is an explicit Action. Every important write gets verified
(ACT → VERIFY) rather than trusting a tool call's success response.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CREATE_CRM_TASK = "create_crm_task"
    SEND_INTERNAL_NOTIFICATION = "send_internal_notification"
    UPDATE_CRM = "update_crm"
    SEND_CUSTOMER_MESSAGE = "send_customer_message"  # approval-required
    FINANCIAL_MUTATION = "financial_mutation"  # approval-required


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    VERIFIED = "verified"


class Action(BaseModel):
    id: str
    type: ActionType

    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    approval_required: bool = False
    status: ActionStatus = ActionStatus.PROPOSED


class ActionResult(BaseModel):
    action_id: str
    success: bool

    # Vendor-side handle used later for verification (e.g. HubSpot task id).
    external_reference: str | None = None
    message: str | None = None
    executed_at: datetime


class VerificationResult(BaseModel):
    action_id: str
    verified: bool

    expected_state: dict[str, Any] = Field(default_factory=dict)
    actual_state: dict[str, Any] = Field(default_factory=dict)
    discrepancies: list[str] = Field(default_factory=list)

    verified_at: datetime


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InvestigationStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
