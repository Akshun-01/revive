"""Connection domain models: per-user upstream provider credentials.

The public `Connection` never carries the secret. `ConnectionCreate` accepts a provider
credentials bag (token / api_key); it is encrypted at rest and resolved at runtime by
ConnectionManager, then handed to the MCP client that implements a provider Protocol.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConnectionProvider(str, Enum):
    SLACK = "slack"
    STRIPE = "stripe"
    HUBSPOT = "hubspot"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class ConnectionCreate(BaseModel):
    provider: ConnectionProvider
    # Provider-specific secret bag, e.g. {"token": "xoxb-..."} or {"api_key": "sk_..."}.
    # Kept as a dict so different providers can carry different auth shapes.
    credentials: dict[str, str]
    scopes: list[str] = Field(default_factory=list)


class Connection(BaseModel):
    """Public view. Never includes credentials."""

    id: str
    provider: ConnectionProvider
    status: ConnectionStatus
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
