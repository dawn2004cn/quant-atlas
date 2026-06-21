"""Fallback router: automatic provider switching on failure.

Phase 7.4 — extracts token usage from LangChain responses and includes
it in the ``ChatResponse.usage`` dict.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.logger import get_logger
from app.domain.ports.llm_adapter_port import ChatMessage, ChatResponse
from app.domain.ports.llm_port import LlmProviderPort

logger = get_logger(__name__)

# Exceptions that trigger automatic fallback
_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)

# Try to include httpx exceptions if available
try:
    import httpx  # type: ignore

    _RETRYABLE_EXCEPTIONS = (
        *_RETRYABLE_EXCEPTIONS,
        httpx.TimeoutException,
        httpx.RemoteProtocolError,
        httpx.NetworkError,
    )
except ImportError:
    logger.warning("Suppressed exception", exc_info=True)
    pass


def _extract_usage(response: Any) -> dict[str, Any]:
    """Extract token usage from a LangChain AIMessage or similar response."""
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


class LlmFallbackRouter:
    """Automatically switches providers on failure.

    Default chain: deepseek → openai → ollama.
    On 5xx or timeout: try next provider in chain.
    On 4xx (e.g. bad API key): raise immediately.
    """

    DEFAULT_CHAIN: list[str] = ["deepseek", "openai", "ollama"]

    def __init__(self, provider_service: LlmProviderPort, default_chain: list[str] | None = None):
        self._provider = provider_service
        self._chain = default_chain or list(self.DEFAULT_CHAIN)

    def set_chain(self, chain: list[str]) -> None:
        """Update the fallback chain."""
        self._chain = list(chain)

    async def call_with_fallback(
        self,
        user_id: int,
        messages: list[ChatMessage],
        logical_model: str | None = None,
        chain: list[str] | None = None,
    ) -> ChatResponse:
        """Try providers in order until one succeeds or all fail.

        Args:
            user_id: Current user.
            messages: Chat messages.
            logical_model: Optional alias to resolve.
            chain: Override fallback chain. Defaults to instance default.

        Returns:
            ChatResponse from the first successful provider (with usage).

        Raises:
            RuntimeError: If all providers in the chain fail.
        """
        active_chain = chain or self._chain
        last_error: Exception | None = None

        for attempt, provider in enumerate(active_chain):
            try:
                config = self._provider.resolve(user_id, provider)
                client = self._provider.build_client(config)
                return await self._call_single_provider(
                    client, messages, config, provider
                )
            except Exception as exc:
                last_error = exc
                status = getattr(exc, "response", None)
                status_code = getattr(status, "status_code", None) if hasattr(status, "status_code") else None

                if status_code and 400 <= status_code < 500:
                    # 4xx = configuration error (bad key, bad model), don't fallback
                    logger.warning(
                        "Provider %s returned 4xx (%d) for user=%d — not falling back. Error: %s",
                        provider, status_code, user_id, exc,
                    )
                    raise

                logger.warning(
                    "Provider %s failed for user=%d (attempt %d/%d): %s",
                    provider, user_id, attempt + 1, len(active_chain), exc,
                )
                continue

        all_providers = ", ".join(active_chain)
        raise RuntimeError(
            f"All LLM providers failed for user={user_id}: [{all_providers}]. "
            f"Last error: {last_error}"
        ) from last_error

    async def _call_single_provider(
        self, client: Any, messages: list[ChatMessage], config: Any, provider_name: str
    ) -> ChatResponse:
        """Call a single provider's LLM client with observability."""
        from langchain_core.messages import HumanMessage, SystemMessage

        start_ts = time.monotonic()
        model = getattr(config, "model_name", provider_name)

        lc_messages = []
        for msg in messages:
            if msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
            else:
                lc_messages.append(HumanMessage(content=msg.content))

        response = await client.ainvoke(lc_messages)
        content = response.content if hasattr(response, "content") else str(response)

        elapsed_ms = round((time.monotonic() - start_ts) * 1000)
        usage = _normalize_usage(_extract_usage(response))

        logger.debug(
            "LLM %s/%s: %dms, tokens=%s",
            provider_name, model, elapsed_ms, usage or "none",
        )

        return ChatResponse(
            content=content.strip(),
            model=model,
            usage=usage,
        )
