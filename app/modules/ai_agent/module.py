"""AI Agent bounded context module declaration."""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_module
from app.modules.health import module_health_check

logger = logging.getLogger(__name__)


@register_module(name="ai_agent", description="AI-powered analysis agents")
class AIAgentContextModule:
    """AI agent context: FinGPT, committees, smart briefing, chart vision."""

    services = []
    routes = [
        "fingpt", "ai_agent", "ai_evidence", "ai_hedge_fund",
        "ai_committee_selection", "investment_committee",
        "quant_ai", "smart_briefing", "chart_vision",
    ]
    config_keys = []
    depends_on = ["market_data"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        _init_ai_committee_selection_service(services, session_factory)

    @staticmethod
    def initialize(container) -> None:
        AIAgentContextModule.wire(container)

    @staticmethod
    def check_health() -> dict:
        return module_health_check("ai_agent", ["redis", "mysql"])


def _init_ai_committee_selection_service(services: Any, session_factory: Any = None) -> None:
    """Initialize AICommitteeSelectionService (migrated from services.py)."""
    if getattr(services, "ai_committee_selection_service", None) is not None:
        return
    try:
        from app.modules.ai_agent.services.ai_committee_selection_service import AICommitteeSelectionService
        repository = None
        if session_factory:
            try:
                from app.infrastructure.repositories.mysql.mysql_ai_committee_selection_repository import (
                    MySQLAICommitteeSelectionRepository,
                )
                repository = MySQLAICommitteeSelectionRepository(session_factory)
            except Exception as repo_exc:
                logger.debug("ai_committee_selection repository not available: %s", repo_exc)
        market_svc = getattr(services, "market_service", None)
        if market_svc is None:
            return
        services.ai_committee_selection_service = AICommitteeSelectionService(
            market_service=market_svc,
            repository=repository,
        )
    except Exception as e:
        logger.warning("ai_agent.module._init_ai_committee_selection_service: %s", e)


__all__ = ["AIAgentContextModule"]
