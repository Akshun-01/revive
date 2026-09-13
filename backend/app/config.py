"""Application settings. Loaded from environment / .env.

Two independent axes - keep them separate:

  * CLIENT TRANSPORT  - how a caller reaches Revive: FastAPI REST or Revive FastMCP.
    Both call the same services; this is NOT a setting, it's just which endpoint is hit.

  * DATA SOURCE       - where evidence comes from: `seed` fixtures or `live` upstream
    (Stripe / HubSpot / Slack MCP). Controlled by `data_source` below.

Upstream Stripe/HubSpot/Slack credentials are NOT config: each user supplies their own
on the frontend and Revive stores them per-user (encrypted) in the connections table.
Env holds only Revive's own infra secrets (DB URL, HF/LangSmith tokens).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from enum import Enum

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# The Postgres checkpointer round-trips our own Pydantic domain models through msgpack.
# We allow that explicitly (JsonPlusSerializer(allowed_msgpack_modules=True) in
# persistence/checkpoint.py); silence the checkpointer serde's per-type deprecation
# notice so it does not clutter demo logs. Only Revive's own types are ever stored.
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)

# Load .env into os.environ so non-REVIVE_-prefixed vars (HF_TOKEN, LANGCHAIN_*)
# reach huggingface_hub and langsmith, which read the process environment directly.
load_dotenv()

# psycopg's async driver (used by the Postgres checkpointer) cannot run on Windows'
# default ProactorEventLoop. Select the SelectorEventLoop policy before any loop is
# created. Safe no-op on other platforms; config is imported before any asyncio.run.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class DataSource(str, Enum):
    SEED = "seed"  # deterministic fixtures - eval + safe demo
    LIVE = "live"  # live upstream Stripe/HubSpot/Slack MCP


class LLMProvider(str, Enum):
    HUGGINGFACE = "huggingface"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REVIVE_",
        env_file=".env",
        extra="ignore",
    )

    # Evidence source for the investigation graph.
    data_source: DataSource = DataSource.SEED

    # LLM for reasoning nodes (diagnose / recoverability) via langchain-huggingface.
    # Token read from env HF_TOKEN (or HUGGINGFACEHUB_API_TOKEN) by huggingface_hub itself.
    llm_provider: LLMProvider = LLMProvider.HUGGINGFACE
    hf_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # When False, reasoning nodes use the deterministic heuristic only (no network).
    # Tests set this off for speed/determinism.
    use_llm: bool = True

    # Tenant: the company running Revive (used in prompts and internal notifications).
    tenant_name: str = "Log0"

    # Persistence. Postgres URL for langgraph checkpoints; blank = in-memory.
    # psycopg format, e.g. postgresql://revive:revive@localhost:5433/revive
    database_url: str | None = None

    # Symmetric key for encrypting stored per-user connection credentials (Fernet).
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    secret_key: str | None = None


settings = Settings()
