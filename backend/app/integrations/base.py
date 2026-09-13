"""Provider Protocols - the seam that isolates vendor/MCP details from the graph.

The LangGraph agent depends only on these interfaces. Two implementations sit
behind them: `seed` (deterministic fixtures) and `mcp` (live Stripe/HubSpot/Slack).
Each collector returns *normalized Evidence*, never raw vendor objects.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.models import ActionResult, Evidence


class CustomerRef(Protocol):
    """Cross-system handle for a resolved customer."""

    id: str
    name: str
    external_ids: dict[str, str]


@runtime_checkable
class BillingProvider(Protocol):
    """Stripe. Financial truth. Read-only for MVP."""

    async def find_customer(self, query: str) -> dict[str, Any]: ...

    async def collect_evidence(self, customer_id: str) -> list[Evidence]: ...


@runtime_checkable
class CRMProvider(Protocol):
    """HubSpot. Account/commercial context + safe internal writes."""

    async def find_company(self, query: str) -> dict[str, Any]: ...

    async def collect_evidence(self, company_id: str) -> list[Evidence]: ...

    async def create_task(self, company_id: str, title: str, body: str, owner_id: str | None) -> ActionResult: ...

    async def get_task(self, task_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class CommunicationProvider(Protocol):
    """Slack (internal) + customer-facing outreach."""

    async def collect_evidence(self, customer_name: str) -> list[Evidence]: ...

    async def send_internal_message(self, channel: str, message: str) -> ActionResult: ...

    async def get_message(self, reference: str) -> dict[str, Any] | None: ...

    # Customer-facing outreach: always approval-gated before execution.
    async def send_customer_message(self, to: str, body: str) -> ActionResult: ...

    async def get_customer_message(self, reference: str) -> dict[str, Any] | None: ...


@runtime_checkable
class BehaviorProvider(Protocol):
    """Userlens. Product behavior. Optional - must not block the core workflow."""

    async def collect_evidence(self, customer_name: str) -> list[Evidence]: ...


class ProviderBundle(Protocol):
    """A full set of providers for one investigation run."""

    billing: BillingProvider
    crm: CRMProvider
    communication: CommunicationProvider
    behavior: BehaviorProvider | None
