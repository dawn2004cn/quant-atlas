"""Universal LLM adapter: unified chat interface regardless of underlying SDK.

Phase 7.4 — adds LLM observability: token usage extraction, latency timing,
and error rate tracking via callbacks on the LangChain client.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.logger import get_logger
from app.domain.ports.llm_adapter_port import ChatMessage, ChatResponse, UniversalLlmPort
from app.modules.system.services.llm_fallback_service import LlmFallbackRouter
from app.modules.system.services.llm_provider_service import LlmProviderService

logger = get_logger(__name__)


# ── Observability helpers ──────────────────────────────────────────────────


def _extract_usage(response: Any) -> dict[str, Any]:
    """Extract token usage from a LangChain AIMessage or similar response.

    Supports multiple extraction strategies:
    1. ``response.usage_metadata`` (LangChain ≥0.2.x)
    2. ``response.response_metadata`` token counts
    3. ``response.usage`` (custom attribute)
    """
    if response is None:
        return {}

    # Strategy 1: usage_metadata (standard LangChain)
    metadata = getattr(response, "usage_metadata", None)
    if metadata and isinstance(metadata, dict):
        return {
            "prompt_tokens": metadata.get("input_tokens") or metadata.get("input_token_count"),
            "completion_tokens": metadata.get("output_tokens") or metadata.get("output_token_count"),
            "total_tokens": metadata.get("total_tokens"),
        }

    # Strategy 2: response_metadata
    resp_meta = getattr(response, "response_metadata", None)
    if resp_meta and isinstance(resp_meta, dict):
        token_info = resp_meta.get("token_usage", {})
        if isinstance(token_info, dict):
            return {
                "prompt_tokens": token_info.get("prompt_tokens"),
                "completion_tokens": token_info.get("completion_tokens"),
                "total_tokens": token_info.get("total_tokens"),
            }

    # Strategy 3: direct usage attribute
    usage = getattr(response, "usage", None)
    if usage and isinstance(usage, dict):
        return usage

    return {}


def _normalize_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize extracted usage to a consistent shape."""
    normalized: dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        val = raw.get(key)
        if val is not None:
            try:
                normalized[key] = int(val)
            except (ValueError, TypeError):
                logger.debug("Token value not convertible to int: %s=%r", key, val)
    return normalized


# ── Callbacks for LangChain observability ──────────────────────────────────


class _ObservabilityCallbacks:
    """LangChain callback container for token/latency tracking.

    Wraps the ``ainvoke`` call to capture timing and usage metadata.
    """

    def __init__(self) -> None:
        self._start_ts: float = 0.0
        self._provider: str = ""
        self._model: str = ""
        self._success: bool = False
        self._tokens: dict[str, Any] = {}

    def before_call(self, provider: str, model: str) -> None:
        self._start_ts = time.monotonic()
        self._provider = provider
        self._model = model
        self._success = False

    def after_call(self, response: Any) -> None:
        elapsed_ms = round((time.monotonic() - self._start_ts) * 1000)
        self._tokens = _normalize_usage(_extract_usage(response))
        self._success = True
        total = self._tokens.get("total_tokens", 0) or 0
        logger.debug(
            "LLM %s/%s: %dms, tokens=%d (prompt=%d, completion=%d)",
            self._provider,
            self._model,
            elapsed_ms,
            total,
            self._tokens.get("prompt_tokens", 0),
            self._tokens.get("completion_tokens", 0),
        )

    @property
    def usage(self) -> dict[str, Any]:
        return dict(self._tokens)

    @property
    def success(self) -> bool:
        return self._success


# ── Adapter ───────────────────────────────────────────────────────────────


class UniversalLlmAdapter(UniversalLlmPort):
    """Facade over LlmProviderService + LlmFallbackRouter.

    All agents call this unified interface regardless of whether
    the backend uses OpenAI, Ollama, Gemini, etc.

    Phase 7.4: Observability is captured via ``_ObservabilityCallbacks``
    on every call, extracting token counts from LangChain responses.

    Usage:
        adapter = UniversalLlmAdapter(
            provider_service=svc,
            fallback_router=fallback_router,
        )
        response = await adapter.send([
            ChatMessage(role="system", content="You are a helpful analyst"),
            ChatMessage(role="user", content="Analyze AAPL"),
        ])
    """

    def __init__(
        self,
        provider_service: LlmProviderService,
        fallback_router: LlmFallbackRouter | None = None,
    ):
        self._provider = provider_service
        self._fallback = fallback_router

    async def send(
        self,
        messages: list[ChatMessage],
        logical_model: str | None = None,
        chain: list[str] | None = None,
    ) -> ChatResponse:
        """Send messages and get response with observability."""
        user_id = self._resolve_user_id()

        if self._fallback is not None:
            return await self._fallback.call_with_fallback(
                user_id=user_id,
                messages=messages,
                logical_model=logical_model,
                chain=chain,
            )

        # Direct path (no fallback): resolve default provider
        config = self._provider.resolve(user_id, "default")
        client = self._provider.build_client(config)
        return await self._call_direct(client, messages, config)

    async def _call_direct(
        self, client: Any, messages: list[ChatMessage], config: Any
    ) -> ChatResponse:
        """Call a single LLM client directly (no fallback chain) with observability."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # Setup observability
        cb = _ObservabilityCallbacks()
        provider = getattr(config, "provider", "default")
        model = getattr(config, "model_name", "unknown")
        cb.before_call(provider, model)

        lc_messages = [
            SystemMessage(content=m.content) if m.role == "system"
            else HumanMessage(content=m.content)
            for m in messages
        ]

        try:
            response = await client.ainvoke(lc_messages)
            cb.after_call(response)
            content = response.content if hasattr(response, "content") else str(response)

            return ChatResponse(
                content=content.strip(),
                model=model,
                usage=cb.usage,
            )
        except Exception as exc:
            logger.warning(
                "LLM call failed: provider=%s model=%s error=%s",
                provider, model, exc,
            )
            return ChatResponse(
                content="",
                model=model,
                usage={"error": str(exc)},
            )

    def _resolve_user_id(self) -> int:
        """Resolve the current user ID from Flask request context.

        In production this uses Flask-Login or request context.
        Returns 0 as a safe default.
        """
        try:
            from flask import request
            from flask_login import current_user

            if current_user and current_user.is_authenticated:
                return current_user.id  # type: ignore[attr-defined]
            if hasattr(request, "quant_atlas_user_id"):
                return request.quant_atlas_user_id  # type: ignore[attr-defined]
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return 0  # system-wide default
