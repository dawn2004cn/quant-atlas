from __future__ import annotations
"""Service Grouping - Organize services by domain responsibility.

This module provides a categorization of application services into logical groups,
following Domain-Driven Design principles and Single Responsibility Principle.
"""


from enum import Enum, auto


class ServiceGroup(Enum):
    """Service category groupings."""

    # Market Data Services
    MARKET_DATA = auto()      # 行情数据
    STOCK_SERVICE = auto()    # 股票服务
    QUOTE_QUERY = auto()      # 报价查询

    # Portfolio Services
    PORTFOLIO = auto()        # 组合管理
    POSITION = auto()         # 持仓管理
    RISK = auto()             # 风险管理

    # Trading Services
    TRADING = auto()          # 交易执行
    ORDER = auto()            # 订单管理
    STRATEGY = auto()         # 策略服务
    SIGNAL = auto()           # 信号/扫描

    # Analysis Services
    ANALYSIS = auto()         # 分析服务
    RESEARCH = auto()         # 研究服务
    PREDICTION = auto()       # 预测服务

    # User Services
    USER = auto()             # 用户服务
    WATCHLIST = auto()        # 自选股
    AUTH = auto()             # 认证

    # Data Services
    DATA_INFRA = auto()       # 数据基础设施
    CACHE = auto()            # 缓存服务
    BACKFILL = auto()         # 数据回填

    # Agent Services
    AGENT = auto()            # Agent服务
    AI_ANALYSIS = auto()      # AI分析
    SWARM = auto()            # 多Agent编排

    # System Services
    MONITORING = auto()       # 监控服务
    TASK = auto()             # 任务调度
    NOTIFICATION = auto()      # 通知服务


SERVICE_GROUP_MAPPING: dict[str, ServiceGroup] = {
    # Market Data
    "MarketApplicationService": ServiceGroup.MARKET_DATA,
    "StockApplicationService": ServiceGroup.STOCK_SERVICE,
    "BasicMarketDataService": ServiceGroup.MARKET_DATA,
    "PoolApplicationService": ServiceGroup.QUOTE_QUERY,

    # Portfolio
    "PortfolioApplicationService": ServiceGroup.PORTFOLIO,
    "PortfolioTradeService": ServiceGroup.PORTFOLIO,
    "PortfolioStressTestService": ServiceGroup.RISK,

    # Risk
    "RiskApplicationService": ServiceGroup.RISK,

    # Trading
    "TradingBotService": ServiceGroup.TRADING,
    "SignalFlagScannerService": ServiceGroup.SIGNAL,
    "ScannerApplicationService": ServiceGroup.SIGNAL,

    # Strategy
    "StrategyApplicationService": ServiceGroup.STRATEGY,
    "StrategyService": ServiceGroup.STRATEGY,
    "StrategyOptimizationService": ServiceGroup.STRATEGY,

    # Analysis
    "StockAnalysisService": ServiceGroup.ANALYSIS,
    "AiAnalysisService": ServiceGroup.AI_ANALYSIS,
    "DiagnosisReportService": ServiceGroup.ANALYSIS,

    # Research
    "AiResearchService": ServiceGroup.RESEARCH,
    "RDAgentRunService": ServiceGroup.RESEARCH,
    "ForwardTestingService": ServiceGroup.RESEARCH,

    # Prediction
    "PredictionApplicationService": ServiceGroup.PREDICTION,
    "AnalysisPredictionService": ServiceGroup.PREDICTION,

    # User
    "UserApplicationService": ServiceGroup.USER,
    "UserService": ServiceGroup.USER,
    "UserLifecycleService": ServiceGroup.USER,
    "UserAccessPolicyService": ServiceGroup.USER,

    # Watchlist
    "WatchlistApplicationService": ServiceGroup.WATCHLIST,
    "WatchlistExperienceService": ServiceGroup.WATCHLIST,
    "WatchlistAgentService": ServiceGroup.WATCHLIST,
    "StockGroupApplicationService": ServiceGroup.WATCHLIST,

    # Data Infrastructure
    "QlibService": ServiceGroup.DATA_INFRA,
    "QlibPipelineService": ServiceGroup.DATA_INFRA,
    "DataInfrastructureService": ServiceGroup.DATA_INFRA,
    "MemoryOptimizationService": ServiceGroup.CACHE,

    # Agent
    "SwarmAgentService": ServiceGroup.AGENT,
    "InvestmentCommitteeService": ServiceGroup.AGENT,
    "AICommitteeService": ServiceGroup.AGENT,

    # Monitoring
    "SentinelService": ServiceGroup.MONITORING,
    "TaskPipelineService": ServiceGroup.TASK,

    # GPCW
    "GpcwApplicationService": ServiceGroup.DATA_INFRA,
}


def get_service_group(service_class_name: str) -> ServiceGroup:
    """Get the group for a service class."""
    return SERVICE_GROUP_MAPPING.get(service_class_name, ServiceGroup.MARKET_DATA)
