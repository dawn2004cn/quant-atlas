"""AI/agent service wiring.

Services for AI analysis, committee, FinGPT, evidence,
adaptive topology, chart vision, and recommendations.

All services are registered via ``register_factory`` / ``register_service``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)

# ── Zero-arg services (simple lambdas) ──────────────────────────────────

def _make_immune_agent_service(reg):
    from app.domain.strategy.strategy_spec import StrategySpec
    from app.modules.strategy.services.analytics.stress_tester import StressTestService
    from app.modules.system.services.immune_agent_service import ImmuneAgentService
    return ImmuneAgentService(
        strategy_spec=StrategySpec(strategy_id="immune_default"),
        stress_tester=StressTestService(),
    )


register_factory("immune_agent_service", _make_immune_agent_service)

def _make_ai_analysis_service(reg):
    from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService
    return AiAnalysisService(
        stock_service=reg.get("stock_service"),
        ai_adapter=reg.get("ai_adapter"),
        fingpt_application_service=reg.get_or_none("fingpt_application_service"),
        prompt_evolution_service=reg.get_or_none("prompt_evolution_service"),
    )


register_factory("ai_analysis_service", _make_ai_analysis_service)

def _make_ai_adapter(reg):
    from app.infrastructure.adapters.ai_analysis_port_adapter import AiAnalysisPortAdapter
    return AiAnalysisPortAdapter()


register_factory("ai_adapter", _make_ai_adapter)


def _make_ai_committee_service(reg):
    from app.modules.ai_agent.services.ai_committee_service import AICommitteeService
    return AICommitteeService()


register_factory("ai_committee_service", _make_ai_committee_service)

def _make_ai_evidence_service(reg):
    from app.config import BASE_DIR
    from app.modules.ai_agent.services.ai_evidence_service import AiEvidenceService
    return AiEvidenceService(
        market_service=reg.get("market_service"),
        stock_service=reg.get("stock_service"),
        fingpt_application_service=reg.get_or_none("fingpt_application_service"),
        signal_observation_service=reg.get_or_none("signal_observation_service"),
        feedback_store_path=BASE_DIR / "instance" / "ai_evidence_feedback.json",
    )


register_factory("ai_evidence_service", _make_ai_evidence_service)

def _make_adaptive_topology_service(reg):
    from app.modules.system.services.adaptive_topology_service import AdaptiveTopologyService
    return AdaptiveTopologyService()


register_factory("adaptive_topology_service", _make_adaptive_topology_service)


def _make_chart_vision_agent_service(reg):
    from app.modules.ai_agent.services.vision.chart_vision_agent_service import ChartVisionAgentService
    return ChartVisionAgentService()


register_factory("chart_vision_agent_service", _make_chart_vision_agent_service)


def _make_recommendation_service(reg):
    from app.modules.strategy.services.strategy.recommendation_service import RecommendationService

    selection = reg.get_or_none("selection_source_service")
    trade_plan = reg.get_or_none("trade_plan_service")
    ai_evidence = reg.get_or_none("ai_evidence_service")
    if selection is None or trade_plan is None or ai_evidence is None:
        logger.warning(
            "recommendation_service skipped: missing deps "
            "(selection=%s trade_plan=%s ai_evidence=%s)",
            selection is not None,
            trade_plan is not None,
            ai_evidence is not None,
        )
        return None
    return RecommendationService(
        selection_source_service=selection,
        signal_flag_service=reg.get_or_none("signal_flag_service"),
        trade_plan_service=trade_plan,
        ai_evidence_service=ai_evidence,
        signal_observation_service=reg.get_or_none("signal_observation_service"),
    )


register_factory("recommendation_service", _make_recommendation_service)


def _make_jarvis_proactive_service(reg):
    from app.modules.ai_agent.services.jarvis_proactive_service import JarvisProactiveService
    return JarvisProactiveService()


register_factory("jarvis_proactive_service", _make_jarvis_proactive_service)


def _make_prompt_evolution_service(reg):
    from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
    return PromptEvolutionService()


register_factory("prompt_evolution_service", _make_prompt_evolution_service)

def _make_decision_feedback_service(reg):
    from app.modules.ai_agent.services.ai.decision_feedback_service import DecisionFeedbackService
    return DecisionFeedbackService(
        user_knowledge_service=reg.get_or_none("user_knowledge_service"),
        prompt_evolution_service=reg.get_or_none("prompt_evolution_service"),
    )

register_factory("decision_feedback_service", _make_decision_feedback_service)

def _make_prompt_decision_bridge_service(reg):
    from app.modules.ai_agent.services.prompt_decision_bridge import PromptDecisionBridge
    return PromptDecisionBridge(feedback_service=reg.get_or_none("decision_feedback_service"))


register_factory("prompt_decision_bridge_service", _make_prompt_decision_bridge_service)


def _make_llm_provider_service(reg):
    from app.application.services.llm_provider_service import LlmProviderService
    from app.core.key_encryption import KeyEncryptionService
    from app.infrastructure.repositories.llm_config_repository import SqlAlchemyUserLlmConfigRepository
    sf = getattr(reg, "_session_factory", None)
    if sf is None:
        raise RuntimeError("session_factory is required for llm_provider_service")
    session = sf()
    kms = KeyEncryptionService()
    repo = SqlAlchemyUserLlmConfigRepository(session, key_encryption=kms)
    return LlmProviderService(repo, key_encryption=kms)


register_factory("llm_provider_service", _make_llm_provider_service)


def _make_llm_fallback_router(reg):
    from app.application.services.llm_fallback_service import LlmFallbackRouter
    return LlmFallbackRouter(reg.get("llm_provider_service"))


register_factory("llm_fallback_router", _make_llm_fallback_router)


def _make_universal_llm_adapter(reg):
    from app.infrastructure.adapters.llm_universal_adapter import UniversalLlmAdapter
    return UniversalLlmAdapter(
        provider_service=reg.get("llm_provider_service"),
        fallback_router=reg.get_or_none("llm_fallback_router"),
    )


register_factory("universal_llm_adapter", _make_universal_llm_adapter)

# ── Complex factories (need settings / session_factory) ─────────────────


def _make_fingpt_application_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.modules.ai_agent.services.fingpt_application_service import FinGPTApplicationService

    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    persistence = _fingpt_persistence(settings, sf)
    return FinGPTApplicationService(
        persistence,
        write_research_sentiment=getattr(settings, "fingpt_write_research_sentiment", True),
        write_research_prediction=getattr(settings, "fingpt_write_research_prediction", True),
        write_ai_analyze=getattr(settings, "fingpt_write_ai_analyze", True),
    )


def _fingpt_persistence(settings: Any, session_factory: Any = None) -> Any | None:
    sf = session_factory
    if sf is None and getattr(settings, "use_mysql", False) and getattr(settings, "mysql", None):
        try:
            from app.infrastructure.database.db_manager import get_db_manager
            sf = get_db_manager().get_session_factory(settings.mysql)
        except Exception as exc:
            logger.debug("fingpt: no mysql session_factory: %s", exc)
            return None
    # Guard: ensure sf is actually callable (scoped_session), not a Session instance
    if sf is not None and not callable(sf):
        logger.warning("fingpt: _session_factory is not callable (type=%s); disabling", type(sf).__name__)
        return None
    if sf is None:
        return None
    from app.infrastructure.adapters.fingpt_adapter import FinGPTRepository
    return FinGPTRepository(sf)


register_factory("fingpt_application_service", _make_fingpt_application_service)


