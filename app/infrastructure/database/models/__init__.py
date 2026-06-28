from __future__ import annotations

"""Models package for easy discovery by Alembic."""


from .advanced import (
    AgentMarketInsight,
    AgentReportInterpretation,
    AICommitteeSelectionRun,
    AICommitteeSelectionTrade,
    AnalysisReport,
    ArchivedNews,
    FinGPTPrediction,
    FinGPTSentiment,
    KronosModel,
    KronosPrediction,
    NewsSymbolMeta,
    OpenBBDataCache,
    OpenBBProviderConfig,
    QuantMLFactor,
    SignalFlagPool,
    YanbaoItem,
)
from .audit import AuditEvent
from .auth import Role, User, UserRoleAssignment
from .collaboration import (
    Team,
    TeamBlackboardEntry,
    TeamMembership,
    Tenant,
    UserKnowledgeProfile,
    UserLifecycleSettings,
)
from .compliance import ComplianceRule, ComplianceViolationLog
from .investment import (
    InvestmentManager,
    ManagerHoldingsSnap,
    ManagerNAV,
    ManagerPositionState,
    ManagerTrade,
    UserRaceAccount,
    UserRaceNAV,
    UserRaceTrade,
)
from .llm_user_config import UserLlmConfig
from .market import (
    BasicDataMeta,
    CNFinanceSnapshot,
    CNFinancialStash,
    CNStockBasic,
    EMHotSector,
    EMHotSectorMember,
    EMHotSectorSnapshot,
    LonghuDaily,
    MarketSentiment,
    MarketSentimentDaily,
    Stock,
    StockGroup,
    StockGroupItem,
    StockHistory,
    TDXBlock,
    TDXBlockItem,
    TDXWatchlist,
    TDXWatchlistItem,
    Watchlist,
)
from .moments import MomentAttachment, MomentComment, MomentLike, MomentPost
from .trading import FTOrder, FTTrade, GatewayConfig, PaymentIntent, PaymentRefund

# Export all models for easier import in env.py
__all__ = [
    "User", "Role", "UserRoleAssignment",
    "Stock", "StockHistory", "Watchlist", "StockGroup", "StockGroupItem",
    "CNStockBasic", "TDXBlock", "TDXBlockItem", "CNFinanceSnapshot",
    "TDXWatchlist", "TDXWatchlistItem", "MarketSentiment", "MarketSentimentDaily",
    "LonghuDaily", "BasicDataMeta", "CNFinancialStash",
    "EMHotSectorSnapshot", "EMHotSector", "EMHotSectorMember",
    "FTTrade", "FTOrder", "GatewayConfig", "PaymentIntent", "PaymentRefund",
    "YanbaoItem", "ArchivedNews", "SignalFlagPool", "AnalysisReport",
    "FinGPTPrediction", "FinGPTSentiment", "KronosModel", "KronosPrediction",
    "OpenBBProviderConfig", "OpenBBDataCache", "QuantMLFactor",
    "AgentMarketInsight", "AgentReportInterpretation", "NewsSymbolMeta",
    "AICommitteeSelectionRun", "AICommitteeSelectionTrade",
    "InvestmentManager", "ManagerNAV", "ManagerTrade", "ManagerHoldingsSnap",
    "ManagerPositionState", "UserRaceAccount", "UserRaceTrade", "UserRaceNAV",
    "MomentPost", "MomentAttachment", "MomentLike", "MomentComment",
    "Tenant", "Team", "TeamMembership", "TeamBlackboardEntry",
    "UserLifecycleSettings", "UserKnowledgeProfile",
    "AuditEvent",
    "ComplianceRule", "ComplianceViolationLog",
    "UserLlmConfig",
]
