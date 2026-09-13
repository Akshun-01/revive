"""Seed provider implementations - deterministic, in-memory.

Satisfies the base Protocols using fixture data. Writes (CRM task, Slack message) are
stored in process-wide class-level dicts, so a later verify node reading through a fresh
bundle instance still sees them - a real ACT -> VERIFY loop without external side effects.
External references are unique, so cross-run bleed is harmless. Powers eval + safe demo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from app.domain.models import ActionResult, Evidence, EvidenceCategory, EvidenceSource
from app.integrations.seed.fixtures import resolve_fixture


def _now() -> datetime:
    return datetime.now(UTC)


def _evidence_for(customer_query: str, *sources: EvidenceSource) -> list[Evidence]:
    fx = resolve_fixture(customer_query)
    if not fx:
        return []
    wanted = set(sources)
    return [e for e in fx.evidence if e.source in wanted]


class SeedBillingProvider:
    async def find_customer(self, query: str) -> dict[str, Any]:
        fx = resolve_fixture(query)
        return fx.customer.model_dump(mode="json") if fx else {}

    async def collect_evidence(self, customer_id: str) -> list[Evidence]:
        return _evidence_for(customer_id, EvidenceSource.STRIPE)


class SeedCRMProvider:
    _tasks: ClassVar[dict[str, dict[str, Any]]] = {}

    async def find_company(self, query: str) -> dict[str, Any]:
        fx = resolve_fixture(query)
        return fx.customer.model_dump(mode="json") if fx else {}

    async def collect_evidence(self, company_id: str) -> list[Evidence]:
        return _evidence_for(company_id, EvidenceSource.HUBSPOT)

    async def create_task(
        self, company_id: str, title: str, body: str, owner_id: str | None
    ) -> ActionResult:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self._tasks[task_id] = {
            "id": task_id,
            "company_id": company_id,
            "title": title,
            "body": body,
            "owner_id": owner_id,
            "created_at": _now().isoformat(),
        }
        return ActionResult(
            action_id="",  # filled by caller
            success=True,
            external_reference=task_id,
            message=f"HubSpot task created: {title}",
            executed_at=_now(),
        )

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)


class SeedCommunicationProvider:
    _messages: ClassVar[dict[str, dict[str, Any]]] = {}
    _customer_messages: ClassVar[dict[str, dict[str, Any]]] = {}

    async def collect_evidence(self, customer_name: str) -> list[Evidence]:
        return _evidence_for(customer_name, EvidenceSource.SLACK)

    async def send_internal_message(self, channel: str, message: str) -> ActionResult:
        ref = f"slack_{uuid.uuid4().hex[:8]}"
        self._messages[ref] = {
            "ref": ref,
            "channel": channel,
            "message": message,
            "ts": _now().isoformat(),
        }
        return ActionResult(
            action_id="",
            success=True,
            external_reference=ref,
            message=f"Notified {channel}",
            executed_at=_now(),
        )

    async def get_message(self, reference: str) -> dict[str, Any] | None:
        return self._messages.get(reference)

    async def send_customer_message(self, to: str, body: str) -> ActionResult:
        ref = f"email_{uuid.uuid4().hex[:8]}"
        self._customer_messages[ref] = {"ref": ref, "to": to, "body": body, "ts": _now().isoformat()}
        return ActionResult(
            action_id="",
            success=True,
            external_reference=ref,
            message=f"Customer message sent to {to}",
            executed_at=_now(),
        )

    async def get_customer_message(self, reference: str) -> dict[str, Any] | None:
        return self._customer_messages.get(reference)


class SeedBehaviorProvider:
    async def collect_evidence(self, customer_name: str) -> list[Evidence]:
        return _evidence_for(customer_name, EvidenceSource.USERLENS)


class SeedProviderBundle:
    """A full provider set. Writes live in class-level stores, shared across instances."""

    def __init__(self) -> None:
        self.billing = SeedBillingProvider()
        self.crm = SeedCRMProvider()
        self.communication = SeedCommunicationProvider()
        self.behavior: SeedBehaviorProvider | None = SeedBehaviorProvider()

    # Category kept for symmetry with future MCP bundle.
    _ = EvidenceCategory
