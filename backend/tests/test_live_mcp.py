"""Live MCP provider plumbing, verified against an in-process mock MCP server.

Proves the client -> tool-call -> normalized Evidence / ActionResult path and graceful
degradation when a connection is missing. Real Stripe/HubSpot/Slack tool schemas differ;
those field mappings are tuned against real endpoints (see provider.py notes).
"""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from app.integrations.mcp.client import McpClient
from app.integrations.mcp.provider import (
    HubSpotLiveProvider,
    SlackLiveProvider,
    StripeLiveProvider,
)


@pytest.fixture
def mock_server():
    m = FastMCP("mock")
    store: dict[str, dict] = {}

    @m.tool
    async def search_documentation(query: str) -> str:
        return f"Stripe: subscription for {query} ended; no payment failure."

    @m.tool
    async def search_crm(query: str) -> str:
        return f"HubSpot: {query} renewal marked closed-lost."

    @m.tool
    async def slack_search_messages(query: str, limit: int = 20) -> str:
        return f"Slack: CSM flagged onboarding friction for {query}."

    @m.tool
    async def create_task(company_id: str, title: str, body: str, owner_id: str | None = None) -> dict:
        tid = f"task_{len(store) + 1}"
        store[tid] = {"id": tid, "title": title, "owner_id": owner_id}
        return store[tid]

    @m.tool
    async def get_task(task_id: str) -> dict:
        return store.get(task_id, {})

    @m.tool
    async def slack_send_message(channel: str, text: str) -> dict:
        ts = f"{len(store) + 1}.000"
        store[ts] = {"ts": ts, "channel": channel, "text": text}
        return store[ts]

    return m


async def test_stripe_evidence(mock_server):
    provider = StripeLiveProvider(McpClient(mock_server))
    evidence = await provider.collect_evidence("Northwind Robotics")
    assert evidence and evidence[0].source.value == "stripe"
    assert "subscription" in evidence[0].finding


async def test_hubspot_task_act_verify(mock_server):
    provider = HubSpotLiveProvider(McpClient(mock_server))
    evidence = await provider.collect_evidence("Northwind Robotics")
    assert evidence and evidence[0].source.value == "hubspot"

    result = await provider.create_task("hs_x", "Recover Northwind", "body", "u_sarah")
    assert result.success and result.external_reference
    task = await provider.get_task(result.external_reference)
    assert task["title"] == "Recover Northwind"


async def test_slack_send_and_read(mock_server):
    provider = SlackLiveProvider(McpClient(mock_server))
    evidence = await provider.collect_evidence("Northwind Robotics")
    assert evidence and evidence[0].source.value == "slack"

    sent = await provider.send_internal_message("#renewals", "heads up")
    assert sent.success and sent.external_reference


async def test_missing_connection_degrades():
    assert await StripeLiveProvider(None).collect_evidence("x") == []
    assert await SlackLiveProvider(None).collect_evidence("x") == []
    result = await HubSpotLiveProvider(None).create_task("c", "t", "b", None)
    assert result.success is False and "not connected" in result.message


def test_resolve_endpoint():
    from app.domain.models.connection import ConnectionProvider
    from app.integrations.mcp.provider import _resolve_endpoint

    # Arga twin: base_url in the connection wins.
    url, token = _resolve_endpoint(
        {"base_url": "https://twin.argalabs.com/stripe/abc", "token": "arga_x"},
        ConnectionProvider.STRIPE,
    )
    assert url == "https://twin.argalabs.com/stripe/abc" and token == "arga_x"

    # No base_url: falls back to the hosted default; api_key accepted as token.
    url, token = _resolve_endpoint({"api_key": "sk_live"}, ConnectionProvider.STRIPE)
    assert url == "https://mcp.stripe.com" and token == "sk_live"

    # No connection: nothing to build.
    assert _resolve_endpoint(None, ConnectionProvider.SLACK) == (None, None)
