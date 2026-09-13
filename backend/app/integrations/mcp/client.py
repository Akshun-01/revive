"""Thin wrapper over the FastMCP client for consuming upstream MCP servers.

Opens a short-lived session per call (simple and robust for the hackathon). `target` is
either a remote MCP URL (bearer token added) or a FastMCP server instance for in-process
testing. `call_tool` returns the tool's structured data, or joined text as a fallback.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _extract(result: Any) -> Any:
    data = getattr(result, "data", None)
    if data is not None:
        return data
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    blocks = getattr(result, "content", None) or []
    texts = [getattr(b, "text", None) for b in blocks if getattr(b, "text", None)]
    return "\n".join(texts) if texts else None


class McpClient:
    def __init__(self, target: Any, token: str | None = None) -> None:
        if isinstance(target, str):
            headers = {"Authorization": f"Bearer {token}"} if token else None
            self._transport: Any = StreamableHttpTransport(target, headers=headers)
        else:
            self._transport = target  # FastMCP instance (in-process) or a prepared transport

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        async with Client(self._transport) as client:
            return _extract(await client.call_tool(name, args))

    async def list_tool_names(self) -> list[str]:
        async with Client(self._transport) as client:
            return [t.name for t in await client.list_tools()]
