"""Research workflow port (application layer depends on this, not on agents)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ResearchPort(ABC):
    """Run multi-agent equity research without coupling callers to LangGraph."""

    @abstractmethod
    async def run_research(
        self,
        ticker: str,
        query: str,
        user_id: int,
        *,
        thread_id: str | None = None,
        llm_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return raw research dict (see ``build_ai_research_response``)."""
        raise NotImplementedError

    def close(self) -> None:
        """Release adapter resources (no-op for stateless adapters)."""
