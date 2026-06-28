"""Infrastructure adapter: LangGraph research via TradingAgentsService."""

from __future__ import annotations

from typing import Any

from app.domain.ports.research_port import ResearchPort


class TradingAgentsResearchAdapter(ResearchPort):
    """Delegates to ``app.agents`` only inside method bodies (lazy import)."""

    def __init__(
        self,
        *,
        fingpt_application_service: Any = None,
        llm_provider_service: Any = None,
    ) -> None:
        self._fingpt = fingpt_application_service
        self._llm_provider_service = llm_provider_service

    async def run_research(
        self,
        ticker: str,
        query: str,
        user_id: int,
        *,
        thread_id: str | None = None,
        llm_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from app.agents.trading_agents_service import TradingAgentsService
        from app.core.llm_config import get_llm
        from app.modules.system.services.config.llm_user_config import (
            build_langchain_llm_from_profile,
        )

        if llm_profile:
            llm = build_langchain_llm_from_profile(llm_profile)
        else:
            llm = get_llm()

        svc = TradingAgentsService(
            llm=llm,
            llm_provider_service=self._llm_provider_service,
            fingpt_application_service=self._fingpt,
        )
        try:
            return await svc.run_research(
                ticker,
                query,
                user_id,
                thread_id=thread_id,
            )
        finally:
            svc.close()


def create_trading_agents_research_adapter(
    *,
    fingpt_application_service: Any = None,
) -> ResearchPort:
    return TradingAgentsResearchAdapter(
        fingpt_application_service=fingpt_application_service,
    )
