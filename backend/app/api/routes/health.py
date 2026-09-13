"""Health check route."""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "data_source": settings.data_source.value,
        "llm_provider": settings.llm_provider.value,
        # postgres = investigations, audit and connections persist; memory = per-process only.
        "persistence": "postgres" if settings.database_url else "memory",
        "llm_enabled": bool(settings.use_llm and (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN"))),
    }
