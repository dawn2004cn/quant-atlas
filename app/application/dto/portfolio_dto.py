"""Application DTOs for portfolio management."""

from typing import Any
from pydantic import BaseModel, Field
from datetime import date


class PortfolioPositionDTO(BaseModel):
    """A single position in a portfolio."""
    symbol: str
    shares: int
    current_price: float
    current_value: float
    target_weight: float
    current_weight: float
    weight_deviation: float
    unrealized_pnl: float
    return_pct: float


class PortfolioSnapshotDTO(BaseModel):
    """Complete portfolio snapshot."""
    portfolio_id: str
    total_value: float
    cash: float
    positions: list[PortfolioPositionDTO] = Field(default_factory=list)
    total_return: float = 0.0
    total_pnl: float = 0.0
    benchmark_return: float = 0.0
    updated_at: str = ""


class OptimizationRequestDTO(BaseModel):
    """Request for portfolio optimization."""
    symbols: list[str] = Field(..., min_length=1)
    method: str = Field(default="markowitz")
    target_return: float | None = None
    risk_aversion: float = Field(default=1.0, ge=0.1, le=10.0)
    analyst_views: dict[str, float] | None = None


class TradeRecordDTO(BaseModel):
    """A single trade transaction."""
    id: int | None = None
    trade_date: date
    symbol: str
    direction: str  # BUY or SELL
    price: float
    quantity: int
    amount: float
    fee: float = 0.0
    user_id: int | None = None


class PortfolioPerformanceDTO(BaseModel):
    """Portfolio performance metrics."""
    date: date
    total_value: float
    daily_return: float
    daily_pnl: float
    cumulative_return: float
    cumulative_pnl: float


class OptimizationResultDTO(BaseModel):
    """Result of portfolio optimization."""
    optimal_weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    method: str
    frontier: list[dict[str, Any]] = Field(default_factory=list)


class RebalanceAlertDTO(BaseModel):
    """Rebalance alert when weight deviation exceeds threshold."""
    symbol: str
    current_weight: float
    target_weight: float
    deviation: float
    action: str
    urgency: str


class AttributionResultDTO(BaseModel):
    """Attribution analysis result."""
    total_return: float
    alpha: float
    beta_timing: float
    style_selection: float
    residual: float
    interpretation: str


class RiskBudgetDTO(BaseModel):
    """Risk budget allocation."""
    symbol: str
    var贡献: float
    weight: float
    marginal_var: float
    risk_contribution_pct: float
