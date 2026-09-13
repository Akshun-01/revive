"""Connection routes: users connect their Stripe / HubSpot / Slack from the frontend.

Tokens are posted once, encrypted, and stored per-user. They are never returned to the
browser. When live mode is wired, ConnectionManager.get_credentials resolves them to build
an authenticated MCP client behind the provider Protocols.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user_id
from app.domain.models.connection import Connection, ConnectionCreate, ConnectionProvider
from app.domain.services.connection_manager import ConnectionError, ConnectionManager

router = APIRouter(prefix="/connections", tags=["connections"])
_manager = ConnectionManager()


@router.get("", response_model=list[Connection])
async def list_connections(user_id: str = Depends(get_current_user_id)) -> list[Connection]:
    return await _manager.list(user_id)


@router.post("", response_model=Connection, status_code=201)
async def create_connection(
    payload: ConnectionCreate, user_id: str = Depends(get_current_user_id)
) -> Connection:
    try:
        return await _manager.upsert(user_id, payload)
    except ConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{provider}", status_code=204)
async def delete_connection(
    provider: ConnectionProvider, user_id: str = Depends(get_current_user_id)
) -> None:
    if not await _manager.delete(user_id, provider):
        raise HTTPException(status_code=404, detail="connection not found")
