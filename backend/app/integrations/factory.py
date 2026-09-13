"""Provider factory. Selects the evidence source from settings.data_source.

Graph code calls `get_provider_bundle()` and never learns which impl it got, nor
which client transport (REST / Revive-MCP) triggered the run - upstream fetch is
transport-agnostic. `live` wires the real Stripe/HubSpot/Slack MCP clients.
"""

from __future__ import annotations

from app.config import DataSource, settings
from app.integrations.seed.provider import SeedProviderBundle


async def get_provider_bundle(user_id: str | None = None):
    """Build the provider set for a run.

    seed: deterministic fixtures (user_id ignored). live: per-user MCP clients built from
    the user's stored connections (Stripe/HubSpot/Slack).
    """
    if settings.data_source is DataSource.SEED:
        return SeedProviderBundle()
    if settings.data_source is DataSource.LIVE:
        from app.integrations.mcp.provider import build_live_bundle

        return await build_live_bundle(user_id or "demo-user")
    raise ValueError(f"Unknown data source: {settings.data_source}")
