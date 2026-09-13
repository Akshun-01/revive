"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "data_source": settings.data_source.value,
        "llm_provider": settings.llm_provider.value,
    }
