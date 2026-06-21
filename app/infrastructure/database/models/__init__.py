from __future__ import annotations
"""Models package for easy discovery by Alembic."""


from .auth import User, Role, UserRoleAssignment
from .market import (
    Stock, StockHistory, Watchlist, StockGroup, StockGroupItem,
    CNStockBasic, TDXBlock, TDXBlockItem, CNFinanceSnapshot,
    TDXWatchlist, TDXWatchlistItem, MarketSentiment, MarketSentimentDaily,
    LonghuDaily, BasicDataMeta, CNFinancialStash,
    EMHotSectorSnapshot, EMHotSector, EMHotSectorMember,
)
from .trading import FTTrade, FTOrder, GatewayConfig, PaymentIntent, PaymentRefund
from .advanced import (
    YanbaoItem, ArchivedNews, SignalFlagPool, AnalysisReport,
    FinGPTPrediction, FinGPTSentiment, KronosModel, KronosPrediction,
    OpenBBProviderConfig, OpenBBDataCache, QuantMLFactor,
    AgentMarketInsight, AgentReportInterpretation, NewsSymbolMeta,
    AICommitteeSelectionRun, AICommitteeSelectionTrade
)
from .investment import (
    InvestmentManager, ManagerNAV, ManagerTrade, ManagerHoldingsSnap,
    ManagerPositionState, UserRaceAccount, UserRaceTrade, UserRaceNAV
)
from .moments import MomentPost, MomentAttachment, MomentLike, MomentComment
from .collaboration import (
    Tenant,
    Team,
    TeamMembership,
    TeamBlackboardEntry,
    UserLifecycleSettings,
    UserKnowledgeProfile,
)
from .audit import AuditEvent
from .compliance import ComplianceRule, ComplianceViolationLog
from .llm_user_config import UserLlmConfig

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
