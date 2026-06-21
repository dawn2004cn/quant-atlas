"""Domain DTO module initialization."""

from .market_data import (
    BarData,
    QuoteData,
    TickData,
    StockProfile,
    MarketStats,
    SignalData,
    PositionData,
    RiskAssessmentData,
)
from .market_data_dto import QuoteDTO, PanoramaDTO
from .agent_workflow_dto import AgentContext

from .global_market_dto import (
    GlobalQuoteDTO,
    GlobalHistoryDTO,
    GlobalMarketConfigDTO,
)

from pydantic import BaseModel
from typing import Any

from .analysis_dto import IndicatorDTO, TrendDTO, SupportResistanceDTO, FibonacciDTO
from .ai_dto import AgentResultDTO, DebateResponseDTO
from .trade_signal_dto import TradeSignalDTO, SignalDirection
from .investment_dto import ManagerStatsDTO, StrategyPerformanceDTO, ManagerDTO
from .market_aggregator_dto import AggregatedQuoteDTO, MarketStatusDTO
from .analytics_dto import AttributionReportDTO, FactorContributionDTO, SectorContributionDTO, StockContributionDTO, MarketEffectDTO
from .risk_dto import RiskAlertDTO, WatchlistRiskReportDTO, RiskLevel
from .system_dto import MemoryStatsDTO, OptimizationResultDTO, TableInfoDTO
from .pipeline_dto import PipelineDTO, PipelineSummaryDTO, DagGraphDTO
from .trade_plan_dto import TradePlanDTO
from .ai_service_dto import AIAnalysisResultDTO, ResearchReportDTO, DebateResultDTO, CommandResultDTO
from .pool_dto import PoolItemDTO, PoolResponseDTO
from .config_dto import ConfigEntryDTO
from .trading_dto import BotStatusDTO, BotActionResponseDTO, BotDetailDTO
from .evidence_dto import EvidenceDTO, EvidenceType

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
