"""SQLAlchemy ORM models for application tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class ConnectionRow(Base):
    """A user's connection to an upstream provider (Slack / Stripe / HubSpot).

    Credentials are stored Fernet-encrypted; the raw token never leaves the backend.
    One connection per (user, provider).
    """

    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String)

    credentials_encrypted: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="connected")
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class InvestigationRow(Base):
    """Queryable application record of an investigation.

    Distinct from the LangGraph checkpoint (opaque, keyed by thread_id, used for resume):
    this row exists so investigations can be listed/filtered per user and rendered without
    replaying the graph. `result` holds the full API result dict.
    """

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # = investigation_id
    user_id: Mapped[str] = mapped_column(String, index=True)

    customer_query: Mapped[str] = mapped_column(String)
    customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, index=True)
    revenue_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_cause: Mapped[str | None] = mapped_column(String, nullable=True)
    recoverability: Mapped[str | None] = mapped_column(String, nullable=True)
    intervention: Mapped[str | None] = mapped_column(String, nullable=True)

    result: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AuditEventRow(Base):
    """Append-only investigation trace: one row per step (tool call, decision, action)."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(String, index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
