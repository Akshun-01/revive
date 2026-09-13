"""Revive MCP server: a small, business-oriented tool surface for external AI clients.

Deliberately NOT generated from the FastAPI routes (FastMCP.from_fastapi) - that would
leak internal endpoints (health, connections CRUD) as tools. Instead we hand-pick a few
business capabilities that call the SAME application services as the REST API, so Claude /
ChatGPT interact with Revive's capabilities, not its implementation (HLD section 6).
"""

from __future__ import annotations

from fastmcp import FastMCP

from app.domain.services.investigation import (
    get_investigation,
    list_investigations,
    resume_investigation,
    run_investigation,
)

mcp = FastMCP("Revive")


@mcp.tool
async def investigate_customer(customer: str) -> dict:
    """Investigate why a customer failed to renew: collect evidence across billing, CRM,
    product usage and internal comms, diagnose the cause, decide recoverability, recommend
    and take a recovery action, and verify it. Returns the full investigation, including a
    pending_action and status 'waiting_for_approval' if a customer-facing action needs sign-off.
    """
    return await run_investigation(customer)


@mcp.tool
async def get_investigation_result(investigation_id: str) -> dict:
    """Fetch a previously started investigation by id (cause, evidence, recoverability,
    recommended intervention, actions taken, verification, and audit trail)."""
    result = await get_investigation(investigation_id)
    return result or {"error": "investigation not found", "investigation_id": investigation_id}


@mcp.tool
async def list_recent_investigations() -> list[dict]:
    """List recent investigations (summaries: customer, status, cause, recoverability)."""
    return await list_investigations()


@mcp.tool
async def resume_recovery(investigation_id: str, approved: bool, edits: dict | None = None) -> dict:
    """Approve (or reject) the pending action of a paused investigation and resume it.
    On approval the action executes and is verified. `edits` optionally overrides action
    parameters as {action_id: {param: value}} before executing."""
    result = await resume_investigation(investigation_id, approved=approved, edits=edits)
    return result or {"error": "investigation not found", "investigation_id": investigation_id}
