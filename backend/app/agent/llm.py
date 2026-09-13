"""HuggingFace chat model access + robust structured-JSON diagnosis.

Small HF instruct models are unreliable at strict tool-calling, so we do not use
`.with_structured_output()`. Instead: prompt for JSON, extract, validate against the
Pydantic schema, retry once. Any failure -> caller falls back to the heuristic.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from app.agent.prompts import DIAGNOSIS_SYSTEM, diagnosis_user_prompt
from app.config import settings
from app.domain.models import Diagnosis, Evidence


def _hf_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")


@lru_cache(maxsize=1)
def get_chat_model():
    """Return a ChatHuggingFace, or None if disabled / no token / import fails."""
    if not settings.use_llm or not _hf_token():
        return None
    try:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        endpoint = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            task="text-generation",
            max_new_tokens=640,
            temperature=0.1,
            huggingfacehub_api_token=_hf_token(),
        )
        return ChatHuggingFace(llm=endpoint)
    except Exception:  # noqa: BLE001 - any init failure degrades to heuristic
        return None


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


def _evidence_for_prompt(evidence: list[Evidence]) -> str:
    slim = [
        {
            "id": e.id,
            "source": e.source.value,
            "category": e.category.value,
            "finding": e.finding,
            "confidence": e.confidence,
            "supports": e.supports,
            "contradicts": e.contradicts,
        }
        for e in evidence
    ]
    return json.dumps(slim, indent=2)


def llm_diagnose(
    customer_name: str, evidence: list[Evidence], heuristic_hint: str
) -> Diagnosis | None:
    """Attempt an LLM diagnosis. Returns None on any failure (caller uses heuristic)."""
    model = get_chat_model()
    if model is None:
        return None

    from langchain_core.messages import HumanMessage, SystemMessage

    user = diagnosis_user_prompt(customer_name, _evidence_for_prompt(evidence), heuristic_hint)
    messages = [SystemMessage(content=DIAGNOSIS_SYSTEM), HumanMessage(content=user)]

    for attempt in range(2):
        try:
            resp = model.invoke(messages)
            raw = resp.content if isinstance(resp.content, str) else str(resp.content)
            return Diagnosis.model_validate_json(_extract_json(raw))
        except Exception as exc:  # noqa: BLE001 - retry once, then give up to heuristic
            if attempt == 0:
                messages.append(
                    HumanMessage(content=f"That was not valid. Error: {exc}. Return ONLY the JSON.")
                )
                continue
            return None
    return None
