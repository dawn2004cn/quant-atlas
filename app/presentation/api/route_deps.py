"""Narrow route dependency bundles (phase 7 — least privilege)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RiskServicePort(Protocol):
    def check_order(self, **kwargs: Any) -> Any: ...

    def check_orders_batch(self, orders: list[Any]) -> Any: ...

    def compute_volatility_target_position(self, **kwargs: Any) -> Any: ...

    def compute_kelly_position(self, **kwargs: Any) -> Any: ...


class MomentsServicePort(Protocol):
    def list_feed(self, **kwargs: Any) -> dict[str, Any]: ...

    def create_post(self, **kwargs: Any) -> dict[str, Any]: ...

    def update_user_post(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_user_post(self, **kwargs: Any) -> dict[str, Any]: ...

    def save_upload(self, file: Any) -> dict[str, Any]: ...

    def toggle_like(self, **kwargs: Any) -> dict[str, Any]: ...

    def list_comments(self, **kwargs: Any) -> dict[str, Any]: ...

    def add_comment(self, **kwargs: Any) -> dict[str, Any]: ...


class InvestmentManagerServicePort(Protocol):
    def ensure_seed_managers(self) -> Any: ...

    def deploy_next_batch(self, **kwargs: Any) -> Any: ...

    def list_managers(self) -> list[Any]: ...

    def leaderboard(self, *, period: str) -> list[Any]: ...

    def manager_detail(self, manager_id: str, *, date: str) -> Any: ...

    def trade_stats_by_manager(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RiskRouteDeps:
    risk_service: RiskServicePort
    enable_legacy_response_fields: bool = True


@dataclass(frozen=True)
class SocialRouteDeps:
    moments_service: MomentsServicePort | None
    investment_manager_service: InvestmentManagerServicePort | None
    enable_legacy_response_fields: bool = True
    enable_celery: bool = False
    task_dispatcher: Any = None
    task_message_store: Any = None


def build_risk_route_deps(ctx: Any) -> RiskRouteDeps:
    return RiskRouteDeps(
        risk_service=getattr(ctx, "risk_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def build_social_route_deps(ctx: Any) -> SocialRouteDeps:
    social = ctx.social
    moments = ctx.moments_service
    if moments is None and social is not None:
        moments = social.moments_service
    im = ctx.investment_manager_service
    if im is None and social is not None:
        im = getattr(social, "investment_manager_service", None)
    return SocialRouteDeps(
        moments_service=moments,
        investment_manager_service=im,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
        enable_celery=bool(ctx.enable_celery),
        task_dispatcher=ctx.task_dispatcher,
        task_message_store=ctx.task_message_store,
    )


def require_moments_service(deps: SocialRouteDeps) -> MomentsServicePort:
    from ...application.errors import ValidationError

    if deps.moments_service is None:
        raise ValidationError(
            "moments_service_unavailable",
            details={"service": "moments_service"},
        )
    return deps.moments_service


@dataclass(frozen=True)
class MarketRouteDeps:
    market_service: Any
    stock_service: Any
    global_market_service: Any | None
    enable_legacy_response_fields: bool = True


@dataclass(frozen=True)
class AiRouteDeps:
    strategy_service: Any | None
    prediction_service: Any | None
    selection_source_service: Any | None
    ai_analysis_service: Any | None
    ai_research_service: Any | None
    rdagent_run_service: Any | None
    swarm_service: Any | None
    enable_legacy_response_fields: bool = True
    enable_qlib: bool = False
    task_message_store: Any = None


@dataclass(frozen=True)
class WorkbenchRouteDeps:
    daily_workbench_service: Any | None
    market_service: Any
    watchlist_service: Any | None
    basic_market_data_service: Any | None
    signal_flag_service: Any | None
    signal_observation_service: Any | None
    fingpt_application_service: Any | None
    news_provider: Any | None
    task_message_store: Any | None
    integration_stack_service: Any | None
    recommendation_service: Any | None
    review_tracking_service: Any | None
    trade_plan_service: Any | None
    enable_legacy_response_fields: bool = True


def build_market_route_deps(ctx: Any) -> MarketRouteDeps:
    return MarketRouteDeps(
        market_service=getattr(ctx, "market_service", None),
        stock_service=getattr(ctx, "stock_service", None),
        global_market_service=ctx.global_market_service,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def build_ai_route_deps(ctx: Any) -> AiRouteDeps:
    ai_research = ctx.ai_research_service
    if ai_research is None and ctx.ai is not None:
        ai_research = ctx.ai.ai_research_service
    return AiRouteDeps(
        strategy_service=ctx.strategy_service,
        prediction_service=ctx.prediction_service,
        selection_source_service=ctx.selection_source_service,
        ai_analysis_service=ctx.ai_analysis_service,
        ai_research_service=ai_research,
        rdagent_run_service=ctx.rdagent_run_service,
        swarm_service=ctx.swarm_service or ctx.rdagent_run_service,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
        enable_qlib=bool(ctx.enable_qlib),
        task_message_store=ctx.task_message_store,
    )


def build_workbench_route_deps(ctx: Any) -> WorkbenchRouteDeps:
    market = ctx.market
    return WorkbenchRouteDeps(
        daily_workbench_service=ctx.daily_workbench_service,
        market_service=getattr(ctx, "market_service", None),
        watchlist_service=(
            market.watchlist_service if market is not None else ctx.watchlist_service
        ),
        basic_market_data_service=(
            market.basic_market_data_service if market is not None else ctx.basic_market_data_service
        ),
        signal_flag_service=(
            market.signal_flag_service if market is not None else ctx.signal_flag_service
        ),
        signal_observation_service=(
            market.signal_observation_service if market is not None else ctx.signal_observation_service
        ),
        fingpt_application_service=ctx.fingpt_application_service,
        news_provider=ctx.news_provider,
        task_message_store=ctx.task_message_store,
        integration_stack_service=ctx.integration_stack_service,
        recommendation_service=ctx.recommendation_service,
        review_tracking_service=ctx.review_tracking_service,
        trade_plan_service=ctx.trade_plan_service,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def require_daily_workbench_service(deps: WorkbenchRouteDeps) -> Any:
    from ...application.errors import ValidationError

    if deps.daily_workbench_service is not None:
        return deps.daily_workbench_service
    if deps.market_service is None:
        raise ValidationError("market_service_unavailable")
    from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService

    task_store = deps.task_message_store
    if task_store is None:
        try:
            from app.modules.system.services.helpers.task_message_wiring import get_task_message_store

            task_store = get_task_message_store()
        except Exception:
            task_store = None

    news_provider = deps.news_provider
    if news_provider is None:
        try:
            from app.modules.system.services.helpers.news_provider_wiring import get_news_provider

            news_provider = get_news_provider()
        except Exception:
            news_provider = None

    return DailyWorkbenchService(
        market_service=deps.market_service,
        watchlist_service=deps.watchlist_service,
        basic_market_data_service=deps.basic_market_data_service,
        signal_flag_service=deps.signal_flag_service,
        signal_observation_service=deps.signal_observation_service,
        fingpt_application_service=deps.fingpt_application_service,
        news_provider=news_provider,
        task_message_store=task_store,
        integration_stack_service=deps.integration_stack_service,
        recommendation_service=deps.recommendation_service,
        review_tracking_service=deps.review_tracking_service,
        trade_plan_service=deps.trade_plan_service,
        health_banner_service=None,
        market_regime_service=None,
    )


def require_swarm_service(deps: AiRouteDeps) -> Any:
    from ...application.errors import ValidationError

    svc = deps.swarm_service
    if svc is None:
        svc = deps.rdagent_run_service
    if svc is None:
        raise ValidationError(
            "swarm_service_unavailable",
            details={"service": "swarm_agent_service or rdagent_run_service"},
        )
    return svc


@dataclass(frozen=True)
class PortfolioUserRouteDeps:
    """Watchlist / stock-group / user admin routes."""

    watchlist_service: Any
    stock_group_service: Any
    market_service: Any | None
    user_service: Any | None
    audit_trail_service: Any | None
    enable_legacy_response_fields: bool = True


def _ctx_service(ctx: Any, name: str) -> Any:
    """Resolve a service from flat ctx fields or grouped market ctx."""
    val = getattr(ctx, name, None)
    if val is not None:
        return val
    market = getattr(ctx, "market", None)
    if market is not None:
        return getattr(market, name, None)
    return None


def build_portfolio_user_route_deps(ctx: Any) -> PortfolioUserRouteDeps:
    market = ctx.market
    return PortfolioUserRouteDeps(
        watchlist_service=_ctx_service(ctx, "watchlist_service"),
        stock_group_service=_ctx_service(ctx, "stock_group_service"),
        market_service=(
            market.market_service if market is not None else ctx.market_service
        ),
        user_service=ctx.user_service,
        audit_trail_service=ctx.user_audit_trail_service,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class PortfolioRouteDeps:
    """Portfolio optimization / import / trade routes."""

    portfolio_service: Any
    watchlist_service: Any | None
    market_service: Any | None
    portfolio_trade_service: Any | None
    enable_legacy_response_fields: bool = True


def build_portfolio_route_deps(ctx: Any) -> PortfolioRouteDeps:
    market = ctx.market
    return PortfolioRouteDeps(
        portfolio_service=getattr(ctx, "portfolio_service", None),
        watchlist_service=ctx.watchlist_service,
        market_service=(
            market.market_service if market is not None else ctx.market_service
        ),
        portfolio_trade_service=getattr(ctx, "portfolio_trade_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def require_portfolio_trade_service(deps: PortfolioRouteDeps) -> Any:
    from ...application.errors import ValidationError

    if deps.portfolio_trade_service is None:
        raise ValidationError(
            "portfolio_trade_service_unavailable",
            details={"service": "portfolio_trade_service"},
        )
    return deps.portfolio_trade_service


@dataclass(frozen=True)
class FinGptRouteDeps:
    fingpt_application_service: Any
    enable_legacy_response_fields: bool = True


def build_fingpt_route_deps(ctx: Any) -> FinGptRouteDeps:
    return FinGptRouteDeps(
        fingpt_application_service=getattr(ctx, "fingpt_application_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class RecommendationRouteDeps:
    recommendation_service: Any
    enable_legacy_response_fields: bool = True


def build_recommendation_route_deps(ctx: Any) -> RecommendationRouteDeps:
    return RecommendationRouteDeps(
        recommendation_service=getattr(ctx, "recommendation_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class MemoryRouteDeps:
    memory_optimization_service: Any


def build_memory_route_deps(ctx: Any) -> MemoryRouteDeps:
    return MemoryRouteDeps(
        memory_optimization_service=getattr(ctx, "memory_optimization_service", None),
    )


@dataclass(frozen=True)
class TaskPipelineRouteDeps:
    task_pipeline_service: Any


def build_task_pipeline_route_deps(ctx: Any) -> TaskPipelineRouteDeps:
    return TaskPipelineRouteDeps(
        task_pipeline_service=getattr(ctx, "task_pipeline_service", None),
    )


@dataclass(frozen=True)
class DataInfrastructureRouteDeps:
    data_infrastructure_service: Any
    task_dispatcher: Any | None
    task_message_store: Any | None
    enable_legacy_response_fields: bool = True


def build_data_infrastructure_route_deps(ctx: Any) -> DataInfrastructureRouteDeps:
    return DataInfrastructureRouteDeps(
        data_infrastructure_service=getattr(ctx, "data_infrastructure_service", None),
        task_dispatcher=ctx.task_dispatcher,
        task_message_store=ctx.task_message_store,
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class DataOptimizerRouteDeps:
    """TDX / scenario optimizer routes (stateless; TDX resolved per request)."""

    enable_legacy_response_fields: bool = False


def build_data_optimizer_route_deps(ctx: Any) -> DataOptimizerRouteDeps:
    return DataOptimizerRouteDeps(
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class HotSectorRouteDeps:
    hot_sector_storage_service: Any | None
    enable_legacy_response_fields: bool = False


def build_hot_sector_route_deps(ctx: Any) -> HotSectorRouteDeps:
    return HotSectorRouteDeps(
        hot_sector_storage_service=getattr(ctx, "hot_sector_storage_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def require_hot_sector_storage_service(deps: HotSectorRouteDeps) -> Any:
    from ...application.errors import ValidationError

    if deps.hot_sector_storage_service is None:
        raise ValidationError(
            "hot_sector_storage_service_unavailable",
            details={"service": "hot_sector_storage_service"},
        )
    return deps.hot_sector_storage_service


@dataclass(frozen=True)
class TdxBaseRouteDeps:
    tdx_base_read_service: Any | None
    enable_legacy_response_fields: bool = False


def build_tdx_base_route_deps(ctx: Any) -> TdxBaseRouteDeps:
    return TdxBaseRouteDeps(
        tdx_base_read_service=getattr(ctx, "tdx_base_read_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


def require_tdx_base_read_service(deps: TdxBaseRouteDeps) -> Any:
    from ...application.errors import ValidationError

    if deps.tdx_base_read_service is None:
        raise ValidationError(
            "tdx_base_read_service_unavailable",
            details={"service": "tdx_base_read_service"},
        )
    return deps.tdx_base_read_service


def require_watchlist_for_portfolio(deps: PortfolioRouteDeps) -> Any:
    from ...application.errors import ValidationError

    if deps.watchlist_service is None:
        raise ValidationError(
            "watchlist_service_unavailable",
            details={"service": "watchlist_service"},
        )
    return deps.watchlist_service


def require_investment_manager_service(deps: SocialRouteDeps) -> InvestmentManagerServicePort:
    from ...application.errors import ValidationError

    if deps.investment_manager_service is None:
        raise ValidationError(
            "investment_manager_service_unavailable",
            details={"service": "investment_manager_service"},
        )
    return deps.investment_manager_service


# ---- Phase 14: Retail Empowerment route deps --------------------------------

@dataclass(frozen=True)
class StrategySynthesisRouteDeps:
    strategy_synthesizer_service: Any | None
    enable_legacy_response_fields: bool = True


def build_strategy_synthesis_route_deps(ctx: Any) -> StrategySynthesisRouteDeps:
    return StrategySynthesisRouteDeps(
        strategy_synthesizer_service=getattr(ctx, "strategy_synthesizer_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class RiskCompanionRouteDeps:
    risk_companion_service: Any | None
    enable_legacy_response_fields: bool = True


def build_risk_companion_route_deps(ctx: Any) -> RiskCompanionRouteDeps:
    return RiskCompanionRouteDeps(
        risk_companion_service=getattr(ctx, "risk_companion_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class WisdomMeshRouteDeps:
    wisdom_mesh_service: Any | None
    enable_legacy_response_fields: bool = True


def build_wisdom_mesh_route_deps(ctx: Any) -> WisdomMeshRouteDeps:
    return WisdomMeshRouteDeps(
        wisdom_mesh_service=getattr(ctx, "wisdom_mesh_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )


@dataclass(frozen=True)
class OneClickRouteDeps:
    one_click_service: Any | None
    enable_legacy_response_fields: bool = True


def build_one_click_route_deps(ctx: Any) -> OneClickRouteDeps:
    return OneClickRouteDeps(
        one_click_service=getattr(ctx, "one_click_service", None),
        enable_legacy_response_fields=bool(ctx.enable_legacy_response_fields),
    )
