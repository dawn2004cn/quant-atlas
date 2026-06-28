"""Market/strategy/data service wiring.

Services related to market data, strategy management,
workbench, and analytics.

All services are registered via ``register_factory`` / ``register_service``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)

# ── Zero-arg services (simple lambdas) ──────────────────────────────────

def _make_strategy_service(reg):
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
    from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService
    from app.infrastructure.providers.strategies import DefaultBacktestProvider, DefaultStrategyProvider
    mp = get_market_data_provider()
    return StrategyApplicationService(
        strategy_provider=DefaultStrategyProvider(market_provider=mp),
        backtest_provider=DefaultBacktestProvider(),
        market_provider=mp,
    )


register_factory("strategy_service", _make_strategy_service)


def _make_strategy_synthesizer_service(reg: Any) -> Any:
    from app.modules.strategy.services.strategy.strategy_synthesizer_service import StrategySynthesizerService

    ai_adapter = reg.get_or_none("ai_adapter") or reg.get_or_none("ai_analysis_service")
    return StrategySynthesizerService(ai_adapter=ai_adapter, nl_parser=None)


register_factory("strategy_synthesizer_service", _make_strategy_synthesizer_service)


def _make_data_lake_manager(reg):
    from app.modules.data.services.data_lake_manager import DataLakeManager
    return DataLakeManager(registry=reg)


register_factory("data_lake_manager", _make_data_lake_manager)


def _make_strategy_wizard_service(reg: Any) -> Any:
    from app.modules.strategy.services.strategy.strategy_wizard_service import StrategyWizardService
    return StrategyWizardService(registry=reg)


register_factory("strategy_wizard_service", _make_strategy_wizard_service)


def _make_smart_daily_briefing_service(reg: Any) -> Any:
    from app.modules.strategy.services.analytics.smart_briefing_service import SmartDailyBriefingService
    return SmartDailyBriefingService(strategy_service=reg.get_or_none("strategy_service"))


register_factory("smart_daily_briefing_service", _make_smart_daily_briefing_service)


def _make_tool_facade_service(_reg: Any) -> Any:
    from app.modules.system.services.tools.tool_facade_service import ToolFacadeService

    return ToolFacadeService()


register_factory("tool_facade_service", _make_tool_facade_service)


def _make_qlib_pipeline_service(reg: Any) -> Any:
    from app.modules.data.services.qlib_pipeline_service import QlibPipelineService
    from app.config import get_settings
    from pathlib import Path

    class _StubDataAccess:
        def fetch_daily_bars(self, symbols, market, start_date, end_date):
            return []

    data_access = _StubDataAccess()
    settings = get_settings()
    base_dir = Path(settings.qlib_export_path) if hasattr(settings, 'qlib_export_path') else Path("instance/qlib_export")
    return QlibPipelineService(
        data_access=data_access,
        base_dir=base_dir,
        tdx_root_path=getattr(settings, "tdx_root_path", None),
    )


register_factory("qlib_pipeline_service", _make_qlib_pipeline_service)


def _make_news_provider(_reg: Any) -> Any:
    from app.modules.system.services.helpers.news_provider_wiring import get_news_provider

    return get_news_provider()


register_factory("news_provider", _make_news_provider)


def _make_task_message_store(_reg: Any) -> Any:
    from app.modules.system.services.helpers.task_message_wiring import get_task_message_store

    return get_task_message_store()


register_factory("task_message_store", _make_task_message_store)


def _resolve_news_provider(reg: Any) -> Any:
    provider = reg.get_or_none("news_provider")
    if provider is not None:
        return provider
    try:
        from app.modules.system.services.helpers.news_provider_wiring import get_news_provider

        return get_news_provider()
    except Exception as exc:
        logger.warning("news_provider fallback failed: %s", exc)
        return None


def _resolve_task_message_store(reg: Any) -> Any:
    store = reg.get_or_none("task_message_store")
    if store is not None:
        return store
    try:
        from app.modules.system.services.helpers.task_message_wiring import get_task_message_store

        return get_task_message_store()
    except Exception as exc:
        logger.warning("task_message_store fallback failed: %s", exc)
        return None


def _make_daily_workbench_service(reg: Any) -> Any:
    from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService
    from app.modules.system.services.system.system_health_banner_service import SystemHealthBannerService
    return DailyWorkbenchService(
        market_service=reg.get("market_service"),
        watchlist_service=reg.get("watchlist_service"),
        signal_flag_service=reg.get_or_none("signal_flag_service"),
        fingpt_application_service=reg.get_or_none("fingpt_application_service"),
        signal_observation_service=reg.get_or_none("signal_observation_service"),
        basic_market_data_service=reg.get_or_none("basic_market_data_service"),
        news_provider=_resolve_news_provider(reg),
        task_message_store=_resolve_task_message_store(reg),
        integration_stack_service=reg.get_or_none("integration_stack_service"),
        recommendation_service=reg.get_or_none("recommendation_service"),
        review_tracking_service=reg.get_or_none("review_tracking_service"),
        trade_plan_service=reg.get_or_none("trade_plan_service"),
        headline_signal_enrichment_service=reg.get_or_none("headline_signal_enrichment_service"),
        health_banner_service=SystemHealthBannerService(),
        market_regime_service=reg.get_or_none("market_regime_service"),
    )


register_factory("daily_workbench_service", _make_daily_workbench_service)


def _make_strategy_optimization_service(_reg: Any) -> Any:
    from app.modules.strategy.services.strategy.strategy_optimization_service import StrategyOptimizationService
    return StrategyOptimizationService()


register_factory("strategy_optimization_service", _make_strategy_optimization_service)


def _make_stock_service_enhanced(_reg: Any) -> Any:
    from app.modules.market_data.services.stock_service import StockServiceEnhanced
    return StockServiceEnhanced()




def _make_ai_research_service(_reg: Any) -> Any:
    from app.modules.ai_agent.services.ai_research_service import AiResearchService
    return AiResearchService()


register_factory("ai_research_service", _make_ai_research_service)


def _make_legacy_migration_service(reg: Any) -> Any:
    from app.modules.data.services.legacy_migration_service import LegacyDataMigrationService
    return LegacyDataMigrationService(registry=reg)


register_factory("legacy_migration_service", _make_legacy_migration_service)


def _make_data_migration_runner(reg: Any) -> Any:
    from app.modules.data.services.data_migration_runner import DataMigrationRunner
    return DataMigrationRunner(registry=reg)


register_factory("data_migration_runner", _make_data_migration_runner)


def _make_fast_backtest_engine(reg: Any) -> Any:
    from app.modules.strategy.services.strategy.fast_backtest_engine import FastBacktestEngine
    return FastBacktestEngine(lake_manager=reg.get("data_lake_manager"))


register_factory("fast_backtest_engine", _make_fast_backtest_engine)


def _make_strategy_sentinel_service(reg: Any) -> Any:
    from app.modules.strategy.services.strategy.strategy_sentinel_service import StrategySentinelService
    return StrategySentinelService(registry=reg)


register_factory("strategy_sentinel_service", _make_strategy_sentinel_service)


def _make_notification_service(reg: Any) -> Any:
    from app.modules.system.services.notification_service import NotificationService
    return NotificationService(registry=reg)


register_factory("notification_service", _make_notification_service)

# ── Complex factories (need settings / session_factory) ─────────────────


def _make_investment_manager_service(reg: Any) -> Any:
    from app.modules.execution.services.investment_manager_service import InvestmentManagerService
    from app.infrastructure.repositories.deps import create_investment_manager_repository, create_stock_cache, create_signal_flag_pool_repository
    from app.config import get_settings
    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_investment_manager_repository(settings, session_factory=sf)
    return InvestmentManagerService(
        repo,
        stock_cache=create_stock_cache(),
        signal_flag_pool=create_signal_flag_pool_repository(settings),
    )


register_factory("investment_manager_service", _make_investment_manager_service)


def _make_moments_service(reg: Any) -> Any:
    from app.modules.data.services.moments_service import MomentsService
    from app.infrastructure.repositories.deps import create_moments_repository
    from app.config import get_settings
    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_moments_repository(settings, session_factory=sf)
    return MomentsService(repo)








def _make_signal_observation_service(reg: Any) -> Any:
    from app.modules.strategy.services.strategy.signal_observation_service import SignalObservationService
    from app.infrastructure.repositories.deps import create_signal_observation_repository
    from app.config import get_settings
    get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_signal_observation_repository(sf)
    return SignalObservationService(observation_repository=repo, store_path=getattr(repo, "_store_path", None))


register_factory("signal_observation_service", _make_signal_observation_service)


def _make_ten_kings_sniper_service(reg: Any) -> Any:
    from app.modules.execution.services.ten_kings_sniper_service import TenKingsSniperService
    from app.config import get_settings
    try:
        from app.infrastructure.repositories.deps import create_sniper_repository
    except ImportError:
        create_sniper_repository = None
    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_sniper_repository(settings, session_factory=sf) if create_sniper_repository else None
    return TenKingsSniperService(repository=repo)


register_factory("ten_kings_sniper_service", _make_ten_kings_sniper_service)


def _make_hot_sector_storage_service(reg: Any) -> Any:
    from app.modules.market_data.services.hot_sector_storage_service import HotSectorStorageService
    from app.config import get_settings
    settings = get_settings()
    return HotSectorStorageService(settings=settings)


register_factory("hot_sector_storage_service", _make_hot_sector_storage_service)


def _make_watchlist_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.deps import (
        create_stock_group_repository,
        create_watchlist_repository,
    )
    from app.modules.market_data.services.watchlist_service import WatchlistApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory

    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    if settings.use_mysql and sf is not None:
        watchlist_repo = create_watchlist_repository(settings, session_factory=sf)
        stock_group_repo = create_stock_group_repository(settings, session_factory=sf)
    else:
        from app.config import CONFIG_DIR
        from app.infrastructure.repositories.common.json_repositories import (
            JsonStockGroupRepository,
            JsonWatchlistRepository,
        )

        watchlist_repo = JsonWatchlistRepository(CONFIG_DIR / "watchlist.json")
        stock_group_repo = JsonStockGroupRepository(
            CONFIG_DIR / "stock_groups.json",
            watchlist_repository=watchlist_repo,
        )
        logger.info("watchlist_service using JSON repositories (use_mysql=%s)", settings.use_mysql)

    return WatchlistApplicationService(
        repository=watchlist_repo,
        stock_group_repository=stock_group_repo,
        market_provider=get_market_data_provider(),
    )


register_factory("watchlist_service", _make_watchlist_service)


def _make_watchlist_agent_service(reg: Any) -> Any:
    from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
    return WatchlistAgentService(
        market_service=reg.get("market_service"),
        stock_service=reg.get("stock_service"),
        watchlist_service=reg.get("watchlist_service"),
        stock_group_service=reg.get("stock_group_service"),
    )


register_factory("watchlist_agent_service", _make_watchlist_agent_service)


def _make_watchlist_experience_service(reg: Any) -> Any:
    from app.modules.market_data.services.watchlist_experience_service import WatchlistExperienceService
    return WatchlistExperienceService(
        watchlist_agent_service=reg.get("watchlist_agent_service"),
        review_tracking_service=reg.get_or_none("review_tracking_service"),
    )


register_factory("watchlist_experience_service", _make_watchlist_experience_service)


def _make_signal_flag_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_signal_flag_pool_repository, create_stock_cache
    from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory

    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    return SignalFlagScannerService(
        stock_service=reg.get("stock_service"),
        stock_cache=create_stock_cache(),
        repository=create_signal_flag_pool_repository(settings, session_factory=sf),
        enable_qlib=bool(getattr(settings, "enable_qlib", False)),
    )


register_factory("signal_flag_service", _make_signal_flag_service)


def _make_stock_group_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_stock_group_repository
    from app.modules.market_data.services.stock_group_service import StockGroupApplicationService
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory

    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    if settings.use_mysql and sf is not None:
        repo = create_stock_group_repository(settings, session_factory=sf)
    else:
        from app.config import CONFIG_DIR
        from app.infrastructure.repositories.common.json_repositories import (
            JsonStockGroupRepository,
            JsonWatchlistRepository,
        )

        watchlist_repo = JsonWatchlistRepository(CONFIG_DIR / "watchlist.json")
        repo = JsonStockGroupRepository(
            CONFIG_DIR / "stock_groups.json",
            watchlist_repository=watchlist_repo,
        )
        logger.info("stock_group_service using JSON repositories (use_mysql=%s)", settings.use_mysql)

    return StockGroupApplicationService(repository=repo)


register_factory("stock_group_service", _make_stock_group_service)


