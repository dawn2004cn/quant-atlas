"""System/collaboration service wiring.

Services for collaboration, mesh, research, and analytics.

All services are registered via ``register_factory``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.bootstrap_components.factory_helpers import zero_arg_service
from app.core.registry import register_factory

logger = logging.getLogger(__name__)

# ── Zero-arg services (lazy import via factory_helpers) ───────────────────

register_factory(
    "arbiter_review_learning_service",
    zero_arg_service(
        "app.modules.system.services.arbiter_review_learning_service",
        "ArbiterReviewLearningService",
    ),
)

register_factory(
    "sequence_chain_service",
    zero_arg_service(
        "app.modules.system.services.sequence_chain_service",
        "SequenceChainService",
    ),
)

register_factory(
    "decision_replay_space_service",
    zero_arg_service(
        "app.modules.system.services.ui.decision_replay_space_service",
        "DecisionReplaySpaceService",
    ),
)

register_factory(
    "voice_briefing_service",
    zero_arg_service(
        "app.modules.strategy.services.analytics.voice_briefing_service",
        "VoiceBriefingService",
    ),
)

register_factory(
    "live_research_document_service",
    zero_arg_service(
        "app.modules.system.services.ui.live_research_document_service",
        "LiveResearchDocumentService",
    ),
)

def _make_strategy_copilot_service(reg):
    from app.modules.strategy.services.strategy.strategy_copilot_service import StrategyCoPilotService
    return StrategyCoPilotService()

register_factory("strategy_copilot_service", _make_strategy_copilot_service)

register_factory(
    "decision_theater_service",
    zero_arg_service(
        "app.modules.system.services.ui.decision_theater_service",
        "DecisionTheaterService",
    ),
)

register_factory(
    "strategy_shadow_service",
    zero_arg_service(
        "app.modules.user.services.user.strategy_shadow_service",
        "StrategyShadowService",
    ),
)

def _make_integration_stack_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.modules.system.services.integration.integration_stack_service import IntegrationStackService
    settings = get_settings()
    return IntegrationStackService(
        settings=settings,
        kronos_service=reg.get_or_none("kronos_service"),
        quantml_factor_service=reg.get_or_none("quantml_factor_service"),
        agentic_analysis_service=reg.get_or_none("agentic_analysis_service"),
        global_market_service=reg.get_or_none("global_market_service"),
        trading_bot_service=reg.get_or_none("trading_bot_service"),
        payment_orchestrator=reg.get_or_none("payment_orchestrator"),
        fingpt_application_service=reg.get_or_none("fingpt_application_service"),
    )


register_factory("integration_stack_service", _make_integration_stack_service)

register_factory(
    "analytics_feature_service",
    zero_arg_service(
        "app.modules.strategy.services.analytics.analytics_feature_service",
        "AnalyticsFeatureService",
    ),
)

register_factory(
    "mesh_gateway_service",
    zero_arg_service(
        "app.modules.system.services.system.mesh_gateway_service",
        "MeshGatewayService",
    ),
)

register_factory(
    "swarm_topology_service",
    zero_arg_service(
        "app.modules.system.services.swarm_topology_service",
        "SwarmTopologyService",
    ),
)

def _make_swarm_agent_service(_reg: Any) -> Any:
    from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService
    return SwarmAgentService(swarm_port=None, skill_port=None)

register_factory("swarm_agent_service", _make_swarm_agent_service)

def _make_swarm_arbiter_service(reg: Any) -> Any:
    from app.modules.system.services.arbiter_service import SwarmArbiterService
    return SwarmArbiterService(
        swarm_service=reg.get_or_none("swarm_agent_service"),
    )

register_factory("swarm_arbiter_service", _make_swarm_arbiter_service)

register_factory(
    "jarvis_semantic_router_service",
    zero_arg_service(
        "app.modules.ai_agent.services.jarvis_semantic_router_service",
        "JarvisSemanticRouterService",
    ),
)

# ── User services (9 individual registrations) ─────────────────────────


def _make_auth_service(reg: Any) -> Any:
    from app.config import CONFIG_DIR
    from app.infrastructure.repositories.common.json_repositories import JsonUserRepository
    from app.modules.user.services.user.auth_service import AuthService

    repo = JsonUserRepository(CONFIG_DIR / "users.json")
    return AuthService(user_repository=repo)


def _make_user_application_service(reg: Any) -> Any:
    from app.config import CONFIG_DIR
    from app.infrastructure.repositories.common.json_repositories import JsonUserRepository
    from app.modules.user.services.user.user_service import UserApplicationService

    repo = JsonUserRepository(CONFIG_DIR / "users.json")
    auth_svc = reg.get("auth_service") if hasattr(reg, "get") else None
    return UserApplicationService(repository=repo, auth_service=auth_svc)


def _make_user_knowledge_service(reg: Any) -> Any:
    from app.modules.user.services.user.user_knowledge_service import UserKnowledgeService

    return UserKnowledgeService()


def _make_archetype_clusterer_service(reg: Any) -> Any:
    from app.modules.user.services.user.archetype_clusterer import ArchetypeClusterer

    return ArchetypeClusterer(
        user_knowledge_service=reg.get_or_none("user_knowledge_service"),
        memory_fabric=reg.get_or_none("memory_fabric"),
    )


def _make_tokenized_alpha_service(reg: Any) -> Any:
    from app.modules.system.services.alpha.tokenized_alpha_service import TokenizedAlphaService

    return TokenizedAlphaService()


def _make_alpha_marketplace_service(reg: Any) -> Any:
    from app.modules.system.services.alpha.alpha_marketplace_service import AlphaMarketplaceService

    broker = getattr(reg, "write_broker", None) or _get_app_write_broker()
    return AlphaMarketplaceService(
        token_service=reg.get_or_none("tokenized_alpha_service"),
        compliance_service=reg.get_or_none("compliance_service"),
        evolution_service=reg.get_or_none("anti_decay_evolution_service"),
        wallet_service=reg.get_or_none("wallet_service"),
        broker=broker,
    )


def _make_wallet_service(reg: Any) -> Any:
    from app.modules.system.services.alpha.wallet_service import WalletService

    broker = _get_app_write_broker()
    return WalletService(broker=broker)


def _make_user_investment_profile_service(reg: Any) -> Any:
    from app.modules.user.services.user.user_investment_profile_service import (
        UserInvestmentProfileService,
    )

    return UserInvestmentProfileService()


def _make_user_access_policy_service(reg: Any) -> Any:
    from app.modules.user.services.user.user_access_policy_service import (
        UserAccessPolicyService,
    )

    return UserAccessPolicyService()


def _make_user_audit_trail_service(reg: Any) -> Any:
    from app.modules.user.services.user.user_audit_trail_service import (
        UserAuditTrailService,
    )

    return UserAuditTrailService()


def _make_user_lifecycle_service(reg: Any) -> Any:
    from app.modules.user.services.user.user_lifecycle_service import UserLifecycleService

    return UserLifecycleService()


def _make_page_preference_service(reg: Any) -> Any:
    from app.modules.user.services.user.page_preference_service import PagePreferenceService

    return PagePreferenceService()


def _make_oauth_provider(reg: Any) -> Any:
    from app.infrastructure.auth.oauth_provider import build_oauth_provider

    return build_oauth_provider()


register_factory("auth_service", _make_auth_service)
register_factory("oauth_provider", _make_oauth_provider)
register_factory("user_service", _make_user_application_service)
register_factory("user_knowledge_service", _make_user_knowledge_service)
register_factory("archetype_clusterer_service", _make_archetype_clusterer_service)
register_factory("tokenized_alpha_service", _make_tokenized_alpha_service)
register_factory("alpha_marketplace_service", _make_alpha_marketplace_service)
register_factory("wallet_service", _make_wallet_service)
register_factory("user_access_policy_service", _make_user_access_policy_service)
register_factory("user_investment_profile_service", _make_user_investment_profile_service)
register_factory("user_audit_trail_service", _make_user_audit_trail_service)
register_factory("user_lifecycle_service", _make_user_lifecycle_service)
register_factory("page_preference_service", _make_page_preference_service)

register_factory(
    "retail_assistant_hub_service",
    zero_arg_service(
        "app.modules.user.services.user.retail_assistant_hub_service",
        "RetailAssistantHubService",
    ),
)

# ── Complex factories (need session_factory) ─────────────────────────────


def _make_collaboration_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_collaboration_repository
    from app.modules.user.services.user.collaboration_service import CollaborationService

    repo = create_collaboration_repository(
        settings=get_settings(),
        session_factory=getattr(reg, "_session_factory", None),
    )
    return CollaborationService(repository=repo)


register_factory("collaboration_service", _make_collaboration_service)

# ── Simple direct-assignment services ───────────────────────────────────

register_factory(
    "meta_arbiter_service",
    zero_arg_service(
        "app.modules.system.services.meta_arbiter_service",
        "MetaArbiterService",
    ),
)

register_factory(
    "cross_team_meta_learning_service",
    zero_arg_service(
        "app.modules.collaboration.services.cross_team_meta_learning_service",
        "CrossTeamMetaLearningService",
    ),
)

register_factory(
    "team_workflow_service",
    zero_arg_service(
        "app.modules.collaboration.services.team_workflow_service",
        "TeamWorkflowService",
    ),
)

register_factory(
    "team_collaboration_service",
    zero_arg_service(
        "app.modules.collaboration.services.team_research_channel_service",
        "TeamResearchChannelService",
    ),
)


def _make_risk_companion_service(_reg: Any) -> Any:
    from app.modules.system.services.risk.risk_companion_service import RiskCompanionService

    return RiskCompanionService()


register_factory("risk_companion_service", _make_risk_companion_service)


def _make_wisdom_mesh_service(_reg: Any) -> Any:
    from app.modules.system.services.mesh.wisdom_mesh_service import WisdomMeshService

    return WisdomMeshService()


register_factory("wisdom_mesh_service", _make_wisdom_mesh_service)


def _make_evolution_arbiter_service(reg: Any) -> Any:
    from app.modules.system.services.system.evolution_arbiter_service import EvolutionArbiterService

    return EvolutionArbiterService(
        meta_arbiter_service=reg.get_or_none("meta_arbiter_service"),
        simulation_gateway_service=reg.get_or_none("simulation_gateway_service"),
    )


register_factory("evolution_arbiter_service", _make_evolution_arbiter_service)


def _make_manifest_service_10(reg: Any) -> Any:
    from app.modules.system.services.mesh.manifest_service_10 import ManifestService10

    return ManifestService10(registry=reg)


register_factory("manifest_service_10", _make_manifest_service_10)


def _make_perception_resonance_service(_reg: Any) -> Any:
    from app.modules.system.services.mesh.perception_resonance_service import (
        PerceptionResonanceService,
    )

    return PerceptionResonanceService()


register_factory("perception_resonance_service", _make_perception_resonance_service)


def _get_app_write_broker() -> Any:
    """Lazy access to write_broker from Flask app context."""
    try:
        from flask import current_app
        return getattr(current_app, "write_broker", None)
    except (ImportError, RuntimeError):
        from app.core.data_write_broker import get_write_broker
        return get_write_broker()

