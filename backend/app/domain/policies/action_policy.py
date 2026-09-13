"""Deterministic action policy. No LLM involvement.

Classifies whether an action needs human approval before execution. Financial and
external-facing actions always require approval; safe internal actions do not.
"""

from __future__ import annotations

from app.domain.models import Action, ActionType

APPROVAL_REQUIRED_TYPES: frozenset[ActionType] = frozenset(
    {
        ActionType.SEND_CUSTOMER_MESSAGE,
        ActionType.FINANCIAL_MUTATION,
    }
)


def requires_approval(action: Action) -> bool:
    return action.type in APPROVAL_REQUIRED_TYPES
