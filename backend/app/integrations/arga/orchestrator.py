"""Arga Labs orchestration over the control MCP (api.argalabs.com/mcp).

Provisions service twins (Stripe / HubSpot / Slack, ...) seeded with a scenario, and
returns their URLs + credentials. Those URLs are then saved as per-user connections
(base_url + token) so Revive's live provider layer investigates against the twins.

The Arga API key is read from env ARGA_API_KEY (an app-level Revive integration key, not a
per-user secret). Creating a twin run consumes an Arga session, so this is driven manually
via scripts/arga_twin.py, never from tests.
"""

from __future__ import annotations

import os
from typing import Any

from app.config import settings
from app.integrations.mcp.client import McpClient


class ArgaError(RuntimeError):
    pass


def _client() -> McpClient:
    key = os.getenv("ARGA_API_KEY")
    if not key:
        raise ArgaError("ARGA_API_KEY is not set in the environment.")
    return McpClient(settings.arga_mcp_url, token=key)


class ArgaOrchestrator:
    async def twin_catalog(self) -> Any:
        """List available twin types (name, label, kind)."""
        return await _client().call_tool("get_twin_catalog", {})

    async def create_twin_run(
        self,
        twins: str,
        scenario_prompt: str | None = None,
        ttl_minutes: int | None = None,
        public: bool = True,
    ) -> Any:
        """Provision one or more twins, optionally seeded from a natural-language scenario.

        `twins` is comma-separated, e.g. "stripe,hubspot,slack". `public=True` yields stable
        base URLs suitable for saving as connections.
        """
        args: dict[str, Any] = {"twins": twins, "public": public}
        if scenario_prompt:
            args["scenario_prompt"] = scenario_prompt
        if ttl_minutes is not None:
            args["ttl_minutes"] = ttl_minutes
        return await _client().call_tool("create_twin_run", args)

    async def get_twin_run(self, run_id: str) -> Any:
        """Get a twin run's status, URLs, env vars, and seed details."""
        return await _client().call_tool("get_twin_run", {"run_id": run_id})
