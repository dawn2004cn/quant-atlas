"""Domain DTO module initialization."""

from typing import Any

from pydantic import BaseModel

from .agent_workflow_dto import AgentContext
from .ai_dto import AgentResultDTO, DebateResponseDTO
from .ai_service_dto import AIAnalysisResultDTO, CommandResultDTO, DebateResultDTO, ResearchReportDTO
from .analysis_dto import FibonacciDTO, IndicatorDTO, SupportResistanceDTO, TrendDTO
from .analytics_dto import (
    AttributionReportDTO,
    FactorContributionDTO,
    MarketEffectDTO,
    SectorContributionDTO,
    StockContributionDTO,
)
from .config_dto import ConfigEntryDTO
from .evidence_dto import EvidenceDTO, EvidenceType
from .global_market_dto import (
    GlobalHistoryDTO,
    GlobalMarketConfigDTO,
    GlobalQuoteDTO,
)
from .investment_dto import ManagerDTO, ManagerStatsDTO, StrategyPerformanceDTO
from .market_aggregator_dto import AggregatedQuoteDTO, MarketStatusDTO
from .market_data import (
    BarData,
    MarketStats,
    PositionData,
    QuoteData,
    RiskAssessmentData,
    SignalData,
    StockProfile,
    TickData,
)
from .market_data_dto import PanoramaDTO, QuoteDTO
from .pipeline_dto import DagGraphDTO, PipelineDTO, PipelineSummaryDTO
from .pool_dto import PoolItemDTO, PoolResponseDTO
from .risk_dto import RiskAlertDTO, RiskLevel, WatchlistRiskReportDTO
from .system_dto import MemoryStatsDTO, OptimizationResultDTO, TableInfoDTO
from .trade_plan_dto import TradePlanDTO
from .trade_signal_dto import SignalDirection, TradeSignalDTO
from .trading_dto import BotActionResponseDTO, BotDetailDTO, BotStatusDTO


class IndicatorResult(BaseModel):
    """Placeholder for IndicatorResult DTO."""
    indicators: dict[str, Any]

class HistoryData(BaseModel):
    """Placeholder for HistoryData DTO."""
    symbol: str
    data: list[Any]

class TradePlanResult(BaseModel):
    """Placeholder for TradePlanResult DTO."""
    plan: dict[str, Any]

__all__ = [
    "BarData",
    "QuoteData",
    "TickData",
    "StockProfile",
    "MarketStats",
    "SignalData",
    "PositionData",
    "RiskAssessmentData",
    "GlobalQuoteDTO",
    "GlobalHistoryDTO",
    "GlobalMarketConfigDTO",
    "IndicatorResult",
    "HistoryData",
    "TradePlanResult",
    "IndicatorDTO",
    "TrendDTO",
    "SupportResistanceDTO",
    "FibonacciDTO",
    "AgentResultDTO",
    "DebateResponseDTO",
    "TradeSignalDTO",
    "SignalDirection",
    "ManagerStatsDTO",
    "StrategyPerformanceDTO",
    "ManagerDTO",
    "AggregatedQuoteDTO",
    "MarketStatusDTO",
    "AttributionReportDTO",
    "FactorContributionDTO",
    "SectorContributionDTO",
    "StockContributionDTO",
    "MarketEffectDTO",
    "RiskAlertDTO",
    "WatchlistRiskReportDTO",
    "RiskLevel",
    "MemoryStatsDTO",
    "OptimizationResultDTO",
    "TableInfoDTO",
    "PipelineDTO",
    "PipelineSummaryDTO",
    "DagGraphDTO",
    "TradePlanDTO",
    "AIAnalysisResultDTO",
    "ResearchReportDTO",
    "DebateResultDTO",
    "CommandResultDTO",
    "PoolItemDTO",
    "PoolResponseDTO",
    "ConfigEntryDTO",
    "BotStatusDTO",
    "BotActionResponseDTO",
    "BotDetailDTO",
    "EvidenceDTO",
    "EvidenceType",
]
