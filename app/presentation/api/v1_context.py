"""API v1 Context - carries dependencies for v1 routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger
from .v1_context_groups import (
    AiCtx,
    MarketCtx,
    SocialCtx,
    SystemCtx,
    UserCtx,
    attach_context_groups,
)


logger = get_logger(__name__)


@dataclass
class ApiV1Context:
    """Context for API v1 routes (flat fields + optional grouped views)."""

    market: MarketCtx | None = None
    user: UserCtx | None = None
    ai: AiCtx | None = None
    social: SocialCtx | None = None
    system: SystemCtx | None = None

    market_service: Any = None
    stock_service: Any = None
    news_provider: Any = None
    fundamental_access: Any = None
    news_archive: Any = None
    qlib_pipeline_service: Any = None
    tool_facade_service: Any = None
    workflow_service: Any = None
    strategy_service: Any = None
    pool_service: Any = None
    ai_analysis_service: Any = None
    ai_research_service: Any = None
    analysis_service: Any = None
    watchlist_service: Any = None
    stock_group_service: Any = None
    user_service: Any = None
    rdagent_run_service: Any = None
    prediction_service: Any = None
    selection_source_service: Any = None
    basic_market_data_service: Any = None
    task_dispatcher: Any = None
    task_message_store: Any = None
    active_job_tracker_service: Any = None
    enable_celery: bool = False
    enable_legacy_response_fields: bool = True
    enable_qlib: bool = False
    enable_rd_agent: bool = False
    signal_flag_service: Any = None
    investment_manager_service: Any = None
    moments_service: Any = None
    integration_stack_service: Any = None
    fingpt_application_service: Any = None
    daily_workbench_service: Any = None
    hot_sector_storage_service: Any = None
    tdx_base_read_service: Any = None
    watchlist_agent_service: Any = None
    watchlist_experience_service: Any = None
    trade_plan_service: Any = None
    signal_observation_service: Any = None
    ai_evidence_service: Any = None
    recommendation_service: Any = None
    strategy_recommendation_service: Any = None
    market_narrative_service: Any = None
    industry_chain_service: Any = None
    diagnosis_report_service: Any = None
    review_tracking_service: Any = None
    user_investment_profile_service: Any = None
    user_access_policy_service: Any = None
    user_audit_trail_service: Any = None
    page_preference_service: Any = None
    user_decision_context_service: Any = None
    user_knowledge_service: Any = None
    user_lifecycle_service: Any = None
    retail_assistant_hub_service: Any = None
    portfolio_service: Any = None
    portfolio_trade_service: Any = None
    ai_hedge_fund_service: Any = None
    risk_service: Any = None
    strategy_optimization_service: Any = None
    research_report_rag_service: Any = None
    investment_committee_service: Any = None
    ai_committee_service: Any = None
    ai_committee_selection_service: Any = None
    command_service: Any = None
    data_infrastructure_service: Any = None
    task_pipeline_service: Any = None
    factor_orthogonalization_service: Any = None
    factor_self_correction_service: Any = None
    memory_optimization_service: Any = None
    global_market_service: Any = None
    swarm_service: Any = None
    swarm_arbiter_service: Any = None
    sequence_chain_service: Any = None
    correction_intent_service: Any = None
    arbiter_review_learning_service: Any = None
    strategy_copilot_service: Any = None
    live_research_document_service: Any = None
    jarvis_proactive_service: Any = None
    collaboration_service: Any = None
    team_blackboard_service: Any = None
    team_research_channel_service: Any = None
    collaborative_backlog_service: Any = None
    cross_team_meta_learning_service: Any = None
    swarm_topology_service: Any = None
    smart_daily_briefing_service: Any = None
    narrative_synthesis_service: Any = None
    simulation_gateway_service: Any = None
    voice_briefing_service: Any = None
    jarvis_semantic_router_service: Any = None
    meta_arbiter_service: Any = None
    evolution_arbiter_service: Any = None
    prompt_evolution_service: Any = None
    alpha_hot_swap_service: Any = None
    shadow_factor_pool: Any = None
    team_workflow_service: Any = None
    decision_replay_space_service: Any = None
    mesh_gateway_service: Any = None
    adaptive_topology_service: Any = None
    strategy_shadow_service: Any = None
    chart_vision_agent_service: Any = None
    borderless_execution_service: Any = None
    self_healing_execution_service: Any = None
    perception_resonance_service: Any = None
    manifest_service_10: Any = None
    hyper_simulator_service: Any = None
    data_truth_guardian_service: Any = None
    decision_theater_service: Any = None
    ten_kings_sniper_service: Any = None

    # Phase 14: Retail Empowerment services
    strategy_synthesizer_service: Any = None
    risk_companion_service: Any = None
    wisdom_mesh_service: Any = None
    one_click_service: Any = None


def create_api_v1_context(api_bundle, task_dispatcher=None, task_message_store=None, enable_celery=False, enable_legacy_response_fields=False, enable_qlib=False, enable_rd_agent=False):
    """Factory function to create ApiV1Context from api_bundle."""
    s = api_bundle.services
    r = api_bundle.repositories

    def _bundle_service(name: str) -> Any:
        try:
            return getattr(s, name, None)
        except Exception:
            logger.warning("Failed to resolve api_bundle.services.%s", name, exc_info=True)
            return None
    
    ctx = ApiV1Context(
        market_service=_bundle_service("market_service"),
        stock_service=_bundle_service("stock_service"),
        news_provider=api_bundle.providers.news_provider,
        fundamental_access=s.fundamental_access,
        news_archive=r.news_archive_repository,
        qlib_pipeline_service=s.qlib_pipeline_service,
        tool_facade_service=s.tool_facade_service,
        workflow_service=s.workflow_service,
        strategy_service=s.strategy_service,
        pool_service=s.pool_service,
        ai_analysis_service=s.ai_analysis_service,
        ai_research_service=s.ai_research_service,
        analysis_service=s.analysis_service,
        watchlist_service=_bundle_service("watchlist_service"),
        stock_group_service=_bundle_service("stock_group_service"),
        user_service=s.user_service,
        rdagent_run_service=s.rdagent_run_service,
        prediction_service=s.prediction_application_service,
        selection_source_service=s.selection_source_service,
        basic_market_data_service=s.basic_market_data_service,
        task_dispatcher=task_dispatcher,
        task_message_store=task_message_store,
        active_job_tracker_service=None,
        enable_celery=enable_celery,
        enable_legacy_response_fields=enable_legacy_response_fields,
        enable_qlib=enable_qlib,
        enable_rd_agent=enable_rd_agent,
        signal_flag_service=_bundle_service("signal_flag_service"),
        investment_manager_service=s.investment_manager_service,
        moments_service=s.moments_service,
        integration_stack_service=s.integration_stack_service,
        fingpt_application_service=s.fingpt_application_service,
        daily_workbench_service=s.daily_workbench_service,
        hot_sector_storage_service=s.hot_sector_storage_service,
        tdx_base_read_service=s.tdx_base_read_service,
        watchlist_agent_service=s.watchlist_agent_service,
        watchlist_experience_service=s.watchlist_experience_service,
        trade_plan_service=s.trade_plan_service,
        signal_observation_service=s.signal_observation_service,
        ai_evidence_service=s.ai_evidence_service,
        recommendation_service=s.recommendation_service,
        strategy_recommendation_service=s.strategy_recommendation_service,
        market_narrative_service=s.market_narrative_service,
        industry_chain_service=s.industry_chain_service,
        diagnosis_report_service=s.diagnosis_report_service,
        review_tracking_service=s.review_tracking_service,
        user_investment_profile_service=s.user_investment_profile_service,
        user_access_policy_service=s.user_access_policy_service,
        user_audit_trail_service=s.user_audit_trail_service,
        page_preference_service=s.page_preference_service,
        user_decision_context_service=s.user_decision_context_service,
        user_knowledge_service=s.user_knowledge_service,
        user_lifecycle_service=s.user_lifecycle_service,
        retail_assistant_hub_service=s.retail_assistant_hub_service,
        portfolio_service=s.portfolio_service,
        portfolio_trade_service=s.portfolio_trade_service,
        ai_hedge_fund_service=s.ai_hedge_fund_service,
        risk_service=s.risk_service,
        strategy_optimization_service=s.strategy_optimization_service,
        research_report_rag_service=s.research_report_rag_service,
        investment_committee_service=s.investment_committee_service,
        ai_committee_service=s.ai_committee_service,
        ai_committee_selection_service=s.ai_committee_selection_service,
        command_service=s.command_service,
        data_infrastructure_service=s.data_infrastructure_service,
        task_pipeline_service=s.task_pipeline_service,
        factor_orthogonalization_service=s.factor_orthogonalization_service,
        factor_self_correction_service=s.factor_self_correction_service,
        memory_optimization_service=s.memory_optimization_service,
        global_market_service=s.global_market_service,
        swarm_service=s.swarm_agent_service or s.rdagent_run_service,
        swarm_arbiter_service=s.swarm_arbiter_service,
        sequence_chain_service=s.sequence_chain_service,
        correction_intent_service=s.correction_intent_service,
        arbiter_review_learning_service=s.arbiter_review_learning_service,
        strategy_copilot_service=s.strategy_copilot_service,
        live_research_document_service=s.live_research_document_service,
        jarvis_proactive_service=s.jarvis_proactive_service,
        collaboration_service=s.collaboration_service,
        team_blackboard_service=s.team_blackboard_service,
        team_research_channel_service=s.team_research_channel_service,
        cross_team_meta_learning_service=s.cross_team_meta_learning_service,
        swarm_topology_service=s.swarm_topology_service,
        smart_daily_briefing_service=s.smart_daily_briefing_service,
        narrative_synthesis_service=s.narrative_synthesis_service,
        simulation_gateway_service=s.simulation_gateway_service,
        voice_briefing_service=s.voice_briefing_service,
        jarvis_semantic_router_service=s.jarvis_semantic_router_service,
        meta_arbiter_service=s.meta_arbiter_service,
        team_workflow_service=s.team_workflow_service,
        decision_replay_space_service=s.decision_replay_space_service,
        mesh_gateway_service=s.mesh_gateway_service,
        adaptive_topology_service=s.adaptive_topology_service,
        strategy_shadow_service=s.strategy_shadow_service,
        chart_vision_agent_service=s.chart_vision_agent_service,
        borderless_execution_service=s.borderless_execution_service,
        self_healing_execution_service=s.self_healing_execution_service,
        perception_resonance_service=s.perception_resonance_service,
        manifest_service_10=s.manifest_service_10,
        hyper_simulator_service=s.hyper_simulator_service,
        data_truth_guardian_service=s.data_truth_guardian_service,
        decision_theater_service=s.decision_theater_service,
        ten_kings_sniper_service=s.ten_kings_sniper_service,
    )

    # ---- Phase 14: Retail Empowerment services (registry factories) ---------
    ctx.strategy_synthesizer_service = getattr(s, "strategy_synthesizer_service", None)
    ctx.risk_companion_service = getattr(s, "risk_companion_service", None)
    ctx.wisdom_mesh_service = getattr(s, "wisdom_mesh_service", None)
    ctx.one_click_service = getattr(s, "one_click_service", None)
    ctx.evolution_arbiter_service = getattr(s, "evolution_arbiter_service", None)
    ctx.active_job_tracker_service = getattr(s, "active_job_tracker_service", None)
    if ctx.active_job_tracker_service is None and task_message_store is not None:
        try:
            from app.modules.system.services.system.active_job_tracker_service import (
                ActiveJobTrackerService,
            )

            ctx.active_job_tracker_service = ActiveJobTrackerService(
                task_message_store=task_message_store,
            )
        except Exception:
            ctx.active_job_tracker_service = None
    try:
        if getattr(ctx, "team_blackboard_service", None) is not None and getattr(ctx, "data_truth_guardian_service", None) is not None:
            ctx.data_truth_guardian_service.set_blackboard_service(ctx.team_blackboard_service)
    except Exception:
        logger.warning("Suppressed exception", exc_info=True)
        pass
    attach_context_groups(ctx)
    pop_fields = [k for k, v in ctx.__dataclass_fields__.items() if getattr(ctx, k, None) is not None and k not in ("market", "user", "ai", "social", "system")]
    ctx_logger = logging.getLogger("app.presentation.api.v1_context")
    ctx_logger.info("ApiV1Context populated fields: %d services available", len(pop_fields))
    for required in ("watchlist_service", "stock_group_service", "market_service"):
        if getattr(ctx, required, None) is None:
            logger.warning("%s unavailable in ApiV1Context", required)

    return ctx
