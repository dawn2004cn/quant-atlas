"""Grouped API v1 context slices (phase-3 slim context)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarketCtx:
    """Market data & watchlist services."""

    market_service: Any = None
    stock_service: Any = None
    analysis_service: Any = None
    basic_market_data_service: Any = None
    watchlist_service: Any = None
    stock_group_service: Any = None
    watchlist_agent_service: Any = None
    watchlist_experience_service: Any = None
    global_market_service: Any = None
    signal_flag_service: Any = None
    signal_observation_service: Any = None


@dataclass
class CollaborationCtx:
    """Collaboration & team research services."""

    collaboration_repository: Any = None
    collaboration_service: Any = None
    team_blackboard_service: Any = None
    team_research_channel_service: Any = None
    team_workflow_service: Any = None
    cross_team_meta_learning_service: Any = None
    meta_arbiter_service: Any = None


@dataclass
class UserCtx:
    """User & profile services."""

    user_service: Any = None
    user_audit_trail_service: Any = None
    user_lifecycle_service: Any = None
    page_preference_service: Any = None
    user_investment_profile_service: Any = None
    user_access_policy_service: Any = None
    user_decision_context_service: Any = None
    user_knowledge_service: Any = None


@dataclass
class AiCtx:
    """AI / quant / agent services."""

    ai_analysis_service: Any = None
    ai_research_service: Any = None
    qlib_pipeline_service: Any = None
    rdagent_run_service: Any = None
    swarm_service: Any = None
    strategy_service: Any = None
    strategy_optimization_service: Any = None
    investment_committee_service: Any = None
    ai_committee_service: Any = None
    ai_committee_selection_service: Any = None
    risk_service: Any = None


@dataclass
class SocialCtx:
    """Social & simulation features."""

    investment_manager_service: Any = None
    moments_service: Any = None
    review_tracking_service: Any = None
    daily_workbench_service: Any = None


@dataclass
class SystemCtx:
    """Infrastructure & pipeline services."""

    task_dispatcher: Any = None
    task_message_store: Any = None
    task_pipeline_service: Any = None
    memory_optimization_service: Any = None
    data_infrastructure_service: Any = None
    integration_stack_service: Any = None
    command_service: Any = None
    active_job_tracker_service: Any = None
    workflow_service: Any = None
    tool_facade_service: Any = None


def attach_context_groups(ctx: Any) -> None:
    """Populate grouped views on ApiV1Context (flat fields unchanged)."""
    ctx.market = MarketCtx(
        market_service=ctx.market_service,
        stock_service=ctx.stock_service,
        analysis_service=ctx.analysis_service,
        basic_market_data_service=ctx.basic_market_data_service,
        watchlist_service=ctx.watchlist_service,
        stock_group_service=ctx.stock_group_service,
        watchlist_agent_service=ctx.watchlist_agent_service,
        watchlist_experience_service=ctx.watchlist_experience_service,
        global_market_service=ctx.global_market_service,
        signal_flag_service=ctx.signal_flag_service,
        signal_observation_service=ctx.signal_observation_service,
    )
    ctx.user = UserCtx(
        user_service=ctx.user_service,
        user_audit_trail_service=ctx.user_audit_trail_service,
        user_lifecycle_service=ctx.user_lifecycle_service,
        page_preference_service=ctx.page_preference_service,
        user_investment_profile_service=ctx.user_investment_profile_service,
        user_access_policy_service=ctx.user_access_policy_service,
        user_decision_context_service=ctx.user_decision_context_service,
        user_knowledge_service=ctx.user_knowledge_service,
    )
    ctx.collaboration = CollaborationCtx(
        collaboration_repository=getattr(ctx, "collaboration_repository", None),
        collaboration_service=getattr(ctx, "collaboration_service", None),
        team_blackboard_service=getattr(ctx, "team_blackboard_service", None),
        team_research_channel_service=getattr(ctx, "team_research_channel_service", None),
        team_workflow_service=getattr(ctx, "team_workflow_service", None),
        cross_team_meta_learning_service=getattr(ctx, "cross_team_meta_learning_service", None),
        meta_arbiter_service=getattr(ctx, "meta_arbiter_service", None),
    )
    ctx.ai = AiCtx(
        ai_analysis_service=ctx.ai_analysis_service,
        ai_research_service=ctx.ai_research_service,
        qlib_pipeline_service=ctx.qlib_pipeline_service,
        rdagent_run_service=ctx.rdagent_run_service,
        swarm_service=ctx.swarm_service,
        strategy_service=ctx.strategy_service,
        strategy_optimization_service=ctx.strategy_optimization_service,
        investment_committee_service=ctx.investment_committee_service,
        ai_committee_service=ctx.ai_committee_service,
        ai_committee_selection_service=ctx.ai_committee_selection_service,
        risk_service=ctx.risk_service,
    )
    ctx.social = SocialCtx(
        investment_manager_service=ctx.investment_manager_service,
        moments_service=ctx.moments_service,
        review_tracking_service=ctx.review_tracking_service,
        daily_workbench_service=ctx.daily_workbench_service,
    )
    ctx.system = SystemCtx(
        task_dispatcher=ctx.task_dispatcher,
        task_message_store=ctx.task_message_store,
        task_pipeline_service=ctx.task_pipeline_service,
        memory_optimization_service=ctx.memory_optimization_service,
        data_infrastructure_service=ctx.data_infrastructure_service,
        integration_stack_service=ctx.integration_stack_service,
        command_service=ctx.command_service,
        active_job_tracker_service=ctx.active_job_tracker_service,
        workflow_service=ctx.workflow_service,
        tool_facade_service=ctx.tool_facade_service,
    )
