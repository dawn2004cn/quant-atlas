"""Domain port: Universal LLM adapter for unified chat interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ChatMessage:
    """Normalized chat message."""

    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class ChatResponse:
    """Normalized chat response."""

    content: str
    model: str
    usage: dict[str, Any] = None  # e.g. {"prompt_tokens": 100, "completion_tokens": 50}


class UniversalLlmPort(Protocol):
    """Unified chat interface independent of underlying LLM SDK."""

    async def send(
        self,
        messages: list[ChatMessage],
        logical_model: str | None = None,
        chain: list[str] | None = None,
    ) -> ChatResponse:
        """Send messages and get response.

        Args:
            messages: Chat messages in order.
            logical_model: e.g. "high_precision", "fast_reasoning" — resolved via alias.
            chain: Fallback provider chain. Defaults to service default.

        Returns:
            Normalized response with content, model name, and token usage.
        """
        ...
