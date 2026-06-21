"""Portfolio & Risk bounded-context DTOs (input/output contracts).

Future home for all Pydantic models consumed/produced by
``app/modules/portfolio_risk/services/*``.
"""

from __future__ import annotations

from app.application.dto.portfolio_dto import (
    AttributionResultDTO,
    OptimizationRequestDTO,
    OptimizationResultDTO,
    PortfolioPerformanceDTO,
    PortfolioPositionDTO,
    PortfolioSnapshotDTO,
    RebalanceAlertDTO,
    RiskBudgetDTO,
    TradeRecordDTO,
)
from app.domain.dto.risk_dto import RiskAlertDTO, WatchlistRiskReportDTO
from app.domain.dto.trade_plan_dto import TradePlanDTO
from app.domain.dto.trade_signal_dto import TradeSignalDTO

__all__ = [
    "AttributionResultDTO",
    "OptimizationRequestDTO",
    "OptimizationResultDTO",
    "PortfolioPerformanceDTO",
    "PortfolioPositionDTO",
    "PortfolioSnapshotDTO",
    "RebalanceAlertDTO",
    "RiskAlertDTO",
    "RiskBudgetDTO",
    "TradePlanDTO",
    "TradeRecordDTO",
    "TradeSignalDTO",
    "WatchlistRiskReportDTO",
]
