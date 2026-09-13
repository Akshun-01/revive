"""Live providers: implement the domain Protocols on top of upstream MCP servers.

Credentials are per-user, resolved from the connections table via ConnectionManager, never
from env. Each provider wraps an McpClient and maps MCP tool results into normalized
Evidence / ActionResult, so the graph stays vendor-agnostic.

IMPORTANT - tuning required: the tool NAMES, argument names, and result field paths below
are best-effort defaults. Stripe / HubSpot / Slack MCP servers expose different tool
schemas; validate and adjust `*_TOOL` / arg names against the real servers once accounts
and endpoints are available. Until then, seed mode remains the demo default. Live evidence
carries no `supports` tags, so the LLM (not the heuristic) classifies the cause in live mode.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.domain.models import (
    ActionResult,
    Evidence,
    EvidenceCategory,
    EvidenceSource,
)
from app.domain.models.connection import ConnectionProvider
from app.integrations.mcp.client import McpClient

# Default hosted MCP endpoints. Verify/override per real integration.
DEFAULT_MCP_URLS: dict[str, str] = {
    "stripe": "https://mcp.stripe.com",
    "hubspot": "https://mcp.hubspot.com",
    "slack": "",  # no official hosted endpoint; user supplies one
}


def _now() -> datetime:
    return datetime.now(UTC)


def _slug(text: str) -> str:
    return text.strip().lower().replace(" ", "-")


def _evidence(source: EvidenceSource, category: EvidenceCategory, text: Any, ref: str) -> list[Evidence]:
    if not text:
        return []
    return [
        Evidence(
            id=f"{source.value}_{uuid.uuid4().hex[:8]}",
            source=source,
            category=category,
            title=f"{source.value} finding",
            finding=str(text)[:2000],
            source_reference=ref,
            timestamp=_now(),
            confidence=0.6,
        )
    ]


class StripeLiveProvider:
    """BillingProvider over the Stripe MCP server."""

    SEARCH_TOOL = "search_documentation"  # TODO: real evidence/read tool
    SEARCH_ARG = "query"

    def __init__(self, client: McpClient | None) -> None:
        self.client = client

    async def find_customer(self, query: str) -> dict[str, Any]:
        # Live resolution is by query; evidence tools key off the name.
        return {"id": _slug(query), "name": query, "external_ids": {"stripe": query}}

    async def collect_evidence(self, customer_id: str) -> list[Evidence]:
        if self.client is None:
            return []
        text = await self.client.call_tool(self.SEARCH_TOOL, {self.SEARCH_ARG: customer_id})
        return _evidence(EvidenceSource.STRIPE, EvidenceCategory.BILLING, text, f"stripe:{customer_id}")


class HubSpotLiveProvider:
    """CRMProvider over the HubSpot MCP server."""

    SEARCH_TOOL = "search_crm"
    SEARCH_ARG = "query"
    CREATE_TASK_TOOL = "create_task"
    GET_TASK_TOOL = "get_task"

    def __init__(self, client: McpClient | None) -> None:
        self.client = client

    async def find_company(self, query: str) -> dict[str, Any]:
        return {"id": _slug(query), "name": query, "external_ids": {"hubspot": query}}

    async def collect_evidence(self, company_id: str) -> list[Evidence]:
        if self.client is None:
            return []
        text = await self.client.call_tool(self.SEARCH_TOOL, {self.SEARCH_ARG: company_id})
        return _evidence(EvidenceSource.HUBSPOT, EvidenceCategory.CRM, text, f"hubspot:{company_id}")

    async def create_task(self, company_id: str, title: str, body: str, owner_id: str | None) -> ActionResult:
        if self.client is None:
            return ActionResult(action_id="", success=False, message="HubSpot not connected", executed_at=_now())
        result = await self.client.call_tool(
            self.CREATE_TASK_TOOL,
            {"company_id": company_id, "title": title, "body": body, "owner_id": owner_id},
        )
        ref = result.get("id") if isinstance(result, dict) else None
        return ActionResult(
            action_id="", success=bool(ref), external_reference=ref,
            message=f"HubSpot task created: {title}", executed_at=_now(),
        )

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        if self.client is None:
            return None
        result = await self.client.call_tool(self.GET_TASK_TOOL, {"task_id": task_id})
        return result if isinstance(result, dict) else None


class SlackLiveProvider:
    """CommunicationProvider over the Slack MCP server."""

    SEARCH_TOOL = "search_messages"
    SEARCH_ARG = "query"
    SEND_TOOL = "send_message"
    GET_TOOL = "get_message"

    def __init__(self, client: McpClient | None) -> None:
        self.client = client

    async def collect_evidence(self, customer_name: str) -> list[Evidence]:
        if self.client is None:
            return []
        text = await self.client.call_tool(self.SEARCH_TOOL, {self.SEARCH_ARG: customer_name})
        return _evidence(EvidenceSource.SLACK, EvidenceCategory.COMMUNICATION, text, f"slack:{customer_name}")

    async def _send(self, target: str, body: str) -> ActionResult:
        if self.client is None:
            return ActionResult(action_id="", success=False, message="Slack not connected", executed_at=_now())
        result = await self.client.call_tool(self.SEND_TOOL, {"target": target, "message": body})
        ref = result.get("ref") or result.get("ts") if isinstance(result, dict) else None
        return ActionResult(
            action_id="", success=bool(ref), external_reference=ref,
            message=f"Slack message sent to {target}", executed_at=_now(),
        )

    async def _get(self, reference: str) -> dict[str, Any] | None:
        if self.client is None:
            return None
        result = await self.client.call_tool(self.GET_TOOL, {"reference": reference})
        return result if isinstance(result, dict) else None

    async def send_internal_message(self, channel: str, message: str) -> ActionResult:
        return await self._send(channel, message)

    async def get_message(self, reference: str) -> dict[str, Any] | None:
        return await self._get(reference)

    async def send_customer_message(self, to: str, body: str) -> ActionResult:
        return await self._send(to, body)

    async def get_customer_message(self, reference: str) -> dict[str, Any] | None:
        return await self._get(reference)


class LiveProviderBundle:
    def __init__(self, billing, crm, communication) -> None:
        self.billing = billing
        self.crm = crm
        self.communication = communication
        self.behavior = None  # Userlens: optional, phase 2


def _token(creds: dict[str, str] | None) -> str | None:
    if not creds:
        return None
    return creds.get("token") or creds.get("api_key")


async def build_live_bundle(user_id: str) -> LiveProviderBundle:
    """Assemble live providers from the user's stored connections.

    A missing connection yields a client-less provider that returns empty evidence and
    reports write actions as not-connected, so partial setups degrade gracefully.
    """
    from app.domain.services.connection_manager import ConnectionManager

    manager = ConnectionManager()

    async def client_for(provider: ConnectionProvider) -> McpClient | None:
        try:
            creds = await manager.get_credentials(user_id, provider)
        except Exception:  # noqa: BLE001 - missing key / not connected -> no client
            creds = None
        token = _token(creds)
        url = DEFAULT_MCP_URLS.get(provider.value) or ""
        if not token or not url:
            return None
        return McpClient(url, token=token)

    return LiveProviderBundle(
        billing=StripeLiveProvider(await client_for(ConnectionProvider.STRIPE)),
        crm=HubSpotLiveProvider(await client_for(ConnectionProvider.HUBSPOT)),
        communication=SlackLiveProvider(await client_for(ConnectionProvider.SLACK)),
    )
