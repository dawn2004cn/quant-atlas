from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
"""Domain ports - interfaces for dependency inversion.

Port files have been consolidated from 20+ modules into ~12 logical groups.
Individual port files (e.g. tdx_local_port.py) may still exist for
backward-compat re-exports but are deprecated.
"""

# ── Core port groups ────────────────────────────────────────────────────

try:
    from .market_ports import *
except ImportError as e:
    logger.warning("__init__.py.market_ports: %s", e)

try:
    from .trading_ports import *
except ImportError as e:
    logger.warning("__init__.py.trading_ports: %s", e)

try:
    from .repository_ports import *
except ImportError as e:
    logger.warning("__init__.py.repository_ports: %s", e)
try:
    from .repository_ports import PaymentGatewayPort, PaymentRepository
except ImportError:
    PaymentGatewayPort = None  # type: ignore[misc, assignment]
    PaymentRepository = None  # type: ignore[misc, assignment]

try:
    from .agent_ports import *
except ImportError as e:
    logger.warning("__init__.py.agent_ports: %s", e)

# ── Domain-level ports ─────────────────────────────────────────────────

try:
    from .portfolio_ports import AttributionAnalysisPort, PortfolioAsset, PortfolioOptimizerPort
except ImportError:
    PortfolioOptimizerPort = None  # type: ignore[misc, assignment]
    AttributionAnalysisPort = None  # type: ignore[misc, assignment]
    PortfolioAsset = None  # type: ignore[misc, assignment]

try:
    from .risk_ports import PositionSizingPort, RiskMetrics, RiskPort, RiskPreFlightPort
except ImportError:
    RiskPreFlightPort = None  # type: ignore[misc, assignment]
    PositionSizingPort = None  # type: ignore[misc, assignment]
    RiskPort = None  # type: ignore[misc, assignment]
    RiskMetrics = None  # type: ignore[misc, assignment]

try:
    from .infrastructure_ports import (
        IAnalyticsEngine,
        IDataMapper,
        IExperimentRepository,
        IIngestorAdapter,
        IMarketDataProvider,
        IMessageStore,
    )
except ImportError as e:
    logger.warning("__init__.py.infrastructure_ports: %s", e)

# ── Port registry ──────────────────────────────────────────────────────

try:
    from .port_registry import (
        IQuoteProvider,
        IStockCache,
        PortRegistry,
        port,
        resolve_infrastructure_port,
        set_fallback_resolver,
    )
except ImportError as e:
    logger.warning("__init__.py.port_registry: %s", e)

# ── Specialized ports ──────────────────────────────────────────────────

try:
    from .research_port import ResearchPort
except ImportError:
    ResearchPort = None  # type: ignore[misc, assignment]

try:
    from .timeseries_port import TimeSeriesDBPort, TimeSeriesPoint
except ImportError as e:
    logger.warning("__init__.py.timeseries_port: %s", e)

try:
    from .llm_port import LlmProviderPort, ResolvedLlmConfig
except ImportError as e:
    logger.warning("__init__.py.llm_port: %s", e)

try:
    from .llm_config_repo_port import UserLlmConfigRepositoryPort
except ImportError as e:
    logger.warning("__init__.py.llm_config_repo_port: %s", e)

try:
    from .llm_adapter_port import ChatMessage, ChatResponse, UniversalLlmPort
except ImportError as e:
    logger.warning("__init__.py.llm_adapter_port: %s", e)

# ── Consolidated port groups (Phase 3) ─────────────────────────────────

try:
    from .tdx_ports import (
        PytdxMarketPort,
        TdxBlockReadPort,
        TdxDaykSyncSessionPort,
        TdxDaykWritePort,
        TdxFinancePort,
        TdxGpcwRepository,
        TdxLocalFilePort,
    )
except ImportError as e:
    logger.warning("__init__.py.tdx_ports: %s", e)

try:
    from .data_source_ports import (
        CnFundamentalsPort,
        CnSectorBoardPort,
        HotSectorStoragePort,
        QuoteCachePort,
        StockCachePort,
    )
except ImportError as e:
    logger.warning("__init__.py.data_source_ports: %s", e)

try:
    from .cache_port import CachePort, get_no_op_cache
except ImportError as e:
    logger.warning("__init__.py.cache_port: %s", e)
    CachePort = None  # type: ignore[misc, assignment]
    get_no_op_cache = None  # type: ignore[misc, assignment]

try:
    from .signal_alert_ports import (
        AlertNotificationChannelPort,
        PriceAlertRepository,
        SignalFlagPoolRepository,
        SignalObservationRepository,
        StrategySnapshotPort,
    )
except ImportError as e:
    logger.warning("__init__.py.signal_alert_ports: %s", e)

__all__ = [
    # Market
    "MarketDataProvider",
    "MarketOverviewPort",
    "QuotePort",
    "HistoryPort",
    "ChipDataPort",
    "NewsProvider",
    "WebSearchProvider",
    "SentimentProvider",
    "FinGPTPersistencePort",
    "IndicatorProvider",
    "IndustryProvider",
    "StrategyProvider",
    "BacktestProvider",
    "TradeRepository",
    "ExchangePort",
    "TradingBotProvider",
    # Repositories
    "IBasicMarketDataRepository",
    "UserRepository",
    "WatchlistRepository",
    "StockGroupRepository",
    "PaymentRepository",
    "PaymentGatewayPort",
    # Agents
    "KronosRepository",
    "KronosPredictorPort",
    "OpenBBRepository",
    "QuantMLFactorRepository",
    "AgentRepository",
    "AgentLLMPort",
    "SwarmOrchestratorPort",
    "ExpertSkillPort",
    "ToolFacadePort",
    "QlibDataProviderPort",
    # Portfolio & Risk
    "PortfolioOptimizerPort",
    "AttributionAnalysisPort",
    "PortfolioAsset",
    "RiskPreFlightPort",
    "PositionSizingPort",
    "RiskPort",
    "RiskMetrics",
    # Infrastructure
    "IExperimentRepository",
    "IMessageStore",
    "IMarketDataProvider",
    "IIngestorAdapter",
    "IDataMapper",
    "IAnalyticsEngine",
    # Registry
    "PortRegistry",
    "port",
    "resolve_infrastructure_port",
    "set_fallback_resolver",
    "IStockCache",
    "IQuoteProvider",
    # Specialized
    "ResearchPort",
    "TimeSeriesDBPort",
    "TimeSeriesPoint",
    "ResolvedLlmConfig",
    "LlmProviderPort",
    "UserLlmConfigRepositoryPort",
    "ChatMessage",
    "ChatResponse",
    "UniversalLlmPort",
    # Consolidated TDX (Phase 3)
    "TdxLocalFilePort",
    "TdxDaykWritePort",
    "TdxDaykSyncSessionPort",
    "TdxGpcwRepository",
    "TdxFinancePort",
    "TdxBlockReadPort",
    "PytdxMarketPort",
    # Consolidated data sources (Phase 3)
    "CnFundamentalsPort",
    "CnSectorBoardPort",
    "HotSectorStoragePort",
    "StockCachePort",
    "QuoteCachePort",
    "CachePort",
    "get_no_op_cache",
    # Consolidated signals/alerts (Phase 3)
    "SignalFlagPoolRepository",
    "SignalObservationRepository",
    "StrategySnapshotPort",
    "AlertNotificationChannelPort",
    "PriceAlertRepository",
]
