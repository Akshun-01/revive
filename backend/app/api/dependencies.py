"""Shared API dependencies.

Auth is a stub for the hackathon: user identity comes from the X-User-Id header, falling
back to a single demo user. Replace with real auth (org/user from a session/JWT) later.
"""

from __future__ import annotations

from fastapi import Header

DEFAULT_USER_ID = "demo-user"


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> str:
    return x_user_id or DEFAULT_USER_ID
