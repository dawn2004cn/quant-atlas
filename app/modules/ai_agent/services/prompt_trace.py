"""Prompt version + hash attachment for LLM call traces."""

from __future__ import annotations

import hashlib
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def prompt_hash(text: str) -> str:
    """Stable SHA-256 prefix for prompt content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def resolve_prompt_version(prompt_id: str = "default") -> str:
    """Resolve active prompt version from evolution service when available."""
    try:
        from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService


        svc = PromptEvolutionService()
        snapshot = svc.get_current_prompt_snapshot(prompt_id)
        return str(snapshot.get("prompt_version") or prompt_id)
    except Exception:
        logger.warning("Suppressed exception", exc_info=True)
        pass
    return prompt_id


def attach_prompt_trace(
    result: dict[str, Any],
    *,
    prompt_id: str,
    prompt_text: str,
    base_version: str | None = None,
    prompt_hash: str | None = None,
) -> dict[str, Any]:
    """Attach prompt_version and prompt_hash to an LLM result dict."""
    version = base_version or resolve_prompt_version(prompt_id)
    result["prompt_id"] = prompt_id
    result["prompt_version"] = version
    result["prompt_hash"] = prompt_hash or prompt_hash_text(prompt_text)
    return result


def prompt_hash_text(text: str) -> str:
    return prompt_hash(text)
