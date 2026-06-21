from __future__ import annotations
"""Dependency injection container for the Quant Atlas application.

Deprecated: bootstrap uses ``bootstrap_components`` + ``service_wiring`` only.
This module remains for legacy scripts/tests that import ``Container`` directly.
"""

from typing import Any

from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.config import get_settings
from app.core.dynamic_settings import DynamicSettings
from app.core.event_bus import get_event_bus

# Domain Ports
from app.domain.ports.repository_ports import (
    UserRepository, WatchlistRepository, StockGroupRepository
)
# Facade imports
from app.facade.market_facade import MarketFacade
from app.facade.backtest_facade import BacktestFacade
from app.facade.ai_facade import AIFacade

# Application Services
from app.modules.user.services.user.auth_service import AuthService
from app.modules.data.services.basic_market_data_service import BasicMarketDataService
from app.infrastructure.repositories.deps import (
    create_default_qlib_pipeline_service,
    create_tdx_dayk_sync_service,
)
from app.modules.user.services.user.user_service import UserApplicationService
from app.modules.market_data.services.watchlist_service import WatchlistApplicationService
from app.modules.market_data.services.stock_group_service import StockGroupApplicationService
from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService
from app.modules.market_data.services.stock_service import StockApplicationService
from app.modules.ai_agent.services.analysis.analysis_service import StockAnalysisService
from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService
from app.modules.ai_agent.services.investment_committee_service import InvestmentCommitteeService
from app.modules.market_data.services.watchlist_risk_service import RiskAlertService
from app.modules.market_data.services.whale_tracker_service import WhaleTrackerService
from app.modules.market_data.services.industry_chain_map_service import IndustryChainMapService
from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService
from app.modules.system.services.system.task_pipeline_service import TaskPipelineService
from app.modules.system.services.system.memory_optimization_service import MemoryOptimizationService
from app.modules.execution.services.trade_plan_service import TradePlanService
from app.modules.ai_agent.services.ai_service import AIAnalysisService as SimpleAiService
from app.application.trading.signal_dispatcher import SignalDispatcher
from app.infrastructure.execution.qmt_executor import QMTExecutor
from app.infrastructure.trading.pre_trade_validator import PreTradeValidator
from app.infrastructure.database.async_mysql_client import AsyncMySQLClient

# Repositories & Infrastructure
from app.infrastructure.repositories.mysql_repositories import (
    MySQLUserRepository, 
    MySQLWatchlistRepository, 
    MySQLStockGroupRepository
)
from app.infrastructure.repositories.basic_market_data_repository import BasicMarketDataRepository as MySQLBasicMarketDataRepository
from app.infrastructure.repositories.async_mysql_repositories import AsyncMySQLUserRepository
from app.infrastructure.providers.rust_indicators import RustIndicatorProvider


def _build_qmt_executor(settings: Any) -> QMTExecutor | None:
    """Factory: only construct QMT when account id is configured."""
    qmt = settings.qmt
    if not qmt.enabled:
        return None
    return QMTExecutor(
        account_id=qmt.account_id or "",
        qmt_path=qmt.qmt_path or "",
    )


class Container(containers.DeclarativeContainer):
    """Main DI Container."""
    
    config = providers.Configuration()
    
    # 1. Base Settings
    settings = providers.Singleton(get_settings)
    dynamic_settings = providers.Singleton(DynamicSettings, config_path="config/settings.json")
    event_bus = providers.Singleton(get_event_bus)

    # 2. Database Infrastructure (Sync)
    db_engine = providers.Singleton(
        create_engine, 
        url=settings.provided.database_uri
    )
    session_factory = providers.Singleton(sessionmaker, bind=db_engine)
    scoped_session_factory = providers.Singleton(scoped_session, session_factory)

    # 3. Database Infrastructure (Async)
    async_db_client = providers.Singleton(
        AsyncMySQLClient, 
        database_uri=settings.provided.database_uri
    )

    # 4. Repositories
    user_repository = providers.Singleton(
        MySQLUserRepository, 
        session_factory=scoped_session_factory
    )
    async_user_repository = providers.Singleton(
        AsyncMySQLUserRepository, 
        session_factory=async_db_client.provided.session_factory
    )
    watchlist_repository = providers.Singleton(
        MySQLWatchlistRepository, 
        session_factory=scoped_session_factory
    )
    stock_group_repository = providers.Singleton(
        MySQLStockGroupRepository, 
        session_factory=scoped_session_factory
    )
    basic_market_data_repository = providers.Singleton(
        MySQLBasicMarketDataRepository,
        # session_factory=scoped_session_factory # Depends on real implementation
    )
    
    # 5. Domain Providers
    indicator_provider = providers.Singleton(RustIndicatorProvider)
    market_data_provider = providers.Object(None) # TODO: Plug in real provider
    
    # 6. Trading Execution
    qmt_executor = providers.Singleton(
        _build_qmt_executor,
        settings=settings,
    )
    pre_trade_validator = providers.Singleton(
        PreTradeValidator, 
        max_trade_amount=1000000.0
    )
    signal_dispatcher = providers.Singleton(
        SignalDispatcher, 
        executor=qmt_executor,
        validator=pre_trade_validator
    )
    
    # 7. Core Application Services
    auth_service = providers.Singleton(
        AuthService,
        user_repository=user_repository
    )
    user_service = providers.Singleton(
        UserApplicationService,
        repository=user_repository
    )

    watchlist_service = providers.Singleton(
        WatchlistApplicationService,
        repository=watchlist_repository,
        stock_group_repository=stock_group_repository
    )
    stock_group_service = providers.Singleton(
        StockGroupApplicationService,
        repository=stock_group_repository
    )
    stock_service = providers.Singleton(
        StockApplicationService,
        indicator_provider=indicator_provider,
        market_provider=market_data_provider
    )
    market_facade = providers.Factory(
        MarketFacade,
        stock_service=stock_service,
        market_service=providers.Object(None),
        watchlist_service=watchlist_service,
        market_data_provider=market_data_provider,
        indicator_provider=indicator_provider,
    )
    stock_analysis_service = providers.Singleton(StockAnalysisService)
    trade_plan_service = providers.Singleton(TradePlanService)
    
    # 8. AI & Agent Services
    ai_analysis_service = providers.Singleton(
        AiAnalysisService,
        stock_service=stock_service,
        ai_adapter=providers.Object(None)
    )
    swarm_service = providers.Singleton(
        SwarmAgentService,
        swarm_port=providers.Object(None),
        skill_port=providers.Object(None)
    )
    investment_committee_service = providers.Singleton(
        InvestmentCommitteeService,
        llm_adapter=providers.Object(None)
    )
    
    # 9. Market Analysis & Monitoring
    risk_alert_service = providers.Singleton(
        RiskAlertService,
        market_provider=market_data_provider,
        indicator_provider=indicator_provider
    )
    whale_tracker_service = providers.Singleton(
        WhaleTrackerService,
        market_provider=market_data_provider
    )
    industry_chain_service = providers.Singleton(
        IndustryChainMapService,
        market_provider=market_data_provider
    )
    watchlist_agent_service = providers.Singleton(
        WatchlistAgentService,
        market_service=stock_service,
        stock_service=stock_service,
        watchlist_service=watchlist_service,
        stock_group_service=stock_group_service
    )
    
    # 10. System & Infrastructure Services
    qlib_pipeline = providers.Singleton(create_default_qlib_pipeline_service)
    tdx_sync_service = providers.Singleton(create_tdx_dayk_sync_service)
    basic_market_data_service = providers.Singleton(
        BasicMarketDataService,
        repository=basic_market_data_repository
    )
    task_pipeline_service = providers.Singleton(TaskPipelineService)
    memory_optimization_service = providers.Singleton(MemoryOptimizationService)
    daily_workbench_service = providers.Singleton(
        DailyWorkbenchService,
        market_service=stock_service,
        watchlist_service=watchlist_service
    )
    # InvestmentManagerService requires repo; wired in bootstrap_components.service_wiring


# Global container instance
container = Container()
