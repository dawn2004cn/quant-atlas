from __future__ import annotations

"""Complete DTO collection for Application Services.

This module provides comprehensive DTOs that replace dict usage throughout the codebase.
Following Phase 7: DTO Standardization plan.
"""


from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ==================== Market DTOs ====================

class QuoteDTO(BaseModel):
    """Real-time quote DTO."""
    code: str
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    amount: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    prev_close: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('change_pct', 'price')
    @classmethod
    def round_values(cls, v):
        return round(v, 2) if v else 0.0


class QuoteBatchDTO(BaseModel):
    """Batch quote response."""
    quotes: list[QuoteDTO]
    total: int
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketOverviewDTO(BaseModel):
    """Market overview DTO."""
    market: str
    status: str = "active"  # active, closed, pre_market, after_hours
    trade_date: str
    index: dict[str, float] = {}  # {name: value}
    total_stocks: int = 0
    gainers: int = 0
    losers: int = 0
    unchanged: int = 0
    turnover: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketSentimentDTO(BaseModel):
    """Market sentiment DTO."""
    market: str
    score: float = 50.0  # 0-100
    level: str = "neutral"  # bullish, neutral, bearish
    emoji: str = "⚖️"
    description: str = ""
    stale: bool = False
    last_update: datetime | None = None
    stats: dict[str, int] = Field(default_factory=dict)  # gainers, losers, neutral, total


class StockProfileDTO(BaseModel):
    """Stock profile/overview DTO."""
    code: str
    name: str = ""
    industry: str = ""
    sector: str = ""
    market: str = "CN"
    list_date: str = ""
    outstanding_shares: float = 0.0  # 亿股
    total_cap: float = 0.0  # 总市值(亿)
    float_shares: float = 0.0  # 流通股本


# ==================== Analysis DTOs ====================

class TechnicalIndicatorDTO(BaseModel):
    """Technical indicator DTO."""
    name: str
    value: float
    signal: str = "neutral"  # bullish, bearish, neutral
    previous_value: float | None = None

    @property
    def change_pct(self) -> float:
        if not self.previous_value:
            return 0.0
        return round((self.value - self.previous_value) / self.previous_value * 100, 2)


class StockAnalysisResultDTO(BaseModel):
    """Complete stock analysis result."""
    code: str
    name: str = ""
    market: str = "CN"

    quote: QuoteDTO | None = None
    profile: StockProfileDTO | None = None

    indicators: list[TechnicalIndicatorDTO] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)

    sentiment: str = "neutral"
    score: float = 50.0  # 0-100 overall score

    recommendation: str = "hold"  # buy, sell, hold
    confidence: float = 50.0

    target_price: float | None = None
    stop_loss: float | None = None

    risks: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)

    timestamp: datetime = Field(default_factory=datetime.now)


class AnalysisResultDTO(BaseModel):
    """Complete analysis result using domain models."""
    code: str
    name: str = ""
    price: float = 0.0

    trend: str = "sideways"
    momentum: float = 0.0

    rsi: float = 50.0
    macd: float = 0.0

    support_levels: list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)

    pattern: str | None = None

    overall_score: float = 50.0
    recommendation: str = "hold"

    analyzed_at: datetime = Field(default_factory=datetime.now)


class TechnicalIndicatorsDTO(BaseModel):
    """Technical indicators DTO."""
    code: str

    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0

    rsi: float = 50.0

    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0

    kdj_k: float = 50.0
    kdj_d: float = 50.0
    kdj_j: float = 50.0

    boll_upper: float = 0.0
    boll_middle: float = 0.0
    boll_lower: float = 0.0

    atr: float = 0.0


# ==================== Signal DTOs ====================

class SignalDTO(BaseModel):
    """Trading signal DTO."""
    id: str = ""
    code: str
    name: str = ""
    signal_type: str  # breakout, mean_reversion, momentum, etc.
    direction: str = "long"  # long, short
    strength: str = "moderate"  # weak, moderate, strong

    price: float = 0.0
    confidence: float = 50.0

    entry_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None

    reason: str = ""
    indicators: dict[str, float] = Field(default_factory=dict)
    source: str = "technical"
    generated_at: datetime | None = None
    expired_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def risk_reward_ratio(self) -> float | None:
        if not all([self.entry_price, self.target_price, self.stop_loss]):
            return None
        reward = abs(self.target_price - self.entry_price)
        risk = abs(self.entry_price - self.stop_loss)
        return round(reward / risk, 2) if risk else None


class SignalFilterDTO(BaseModel):
    """Signal filter criteria DTO."""
    signal_types: list[str] | None = None
    min_strength: str | None = None  # weak, moderate, strong
    code_list: list[str] | None = None
    direction: str | None = None  # long, short
    min_confidence: float = 0.0
    start_date: datetime | None = None
    end_date: datetime | None = None


class SignalListDTO(BaseModel):
    """Signal list response DTO."""
    signals: list[SignalDTO] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class SignalCreateDTO(BaseModel):
    """Signal creation request DTO."""
    code: str
    name: str = ""
    signal_type: str
    direction: str = "long"
    strength: str = "moderate"
    price: float
    confidence: float = 50.0
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    reason: str = ""
    source: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResultDTO(BaseModel):
    """Stock scan result."""
    scan_name: str
    signals: list[SignalDTO] = Field(default_factory=list)
    total_scanned: int = 0
    matched: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== Portfolio DTOs ====================

class PositionDTO(BaseModel):
    """Position DTO."""
    id: str = ""
    code: str
    name: str = ""
    side: str = "long"  # long, short

    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0

    total_cost: float = 0.0
    total_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0

    weight: float = 0.0
    holding_days: int = 0

    opened_at: datetime | None = None
    closed_at: datetime | None = None
    status: str = "open"  # open, closed

    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class PortfolioSummaryDTO(BaseModel):
    """Portfolio summary DTO."""
    total_value: float = 0.0
    total_cost: float = 0.0
    total_pnl: float = 0.0
    pnl_pct: float = 0.0

    cash: float = 0.0
    position_count: int = 0
    winning_positions: int = 0
    losing_positions: int = 0

    name: str = "Default Portfolio"
    initial_cash: float = 100000.0
    current_value: float = 100000.0
    total_pnl_pct: float = 0.0
    positions: list[PositionDTO] = Field(default_factory=list)
    occupied: float = 0.0

    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

    updated_at: datetime = Field(default_factory=datetime.now)


class PortfolioDTO(BaseModel):
    """Full portfolio DTO."""
    id: str = ""
    name: str = "Default Portfolio"
    initial_capital: float = 100000.0
    current_capital: float = 100000.0
    cash: float = 100000.0
    positions: list[PositionDTO] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PortfolioMetricsDTO(BaseModel):
    """Portfolio performance metrics DTO."""
    total_value: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    volatility: float = 0.0
    beta: float = 1.0
    alpha: float = 0.0


class OptimizationRequestDTO(BaseModel):
    """Portfolio optimization request DTO."""
    symbols: list[str]
    method: str = "markowitz"  # markowitz, black_litterman, risk_parity
    target_return: float | None = None
    risk_aversion: float = 1.0


class OptimizationResultDTO(BaseModel):
    """Portfolio optimization result DTO."""
    optimal_weights: dict[str, float] = Field(default_factory=dict)
    expected_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    method: str = "markowitz"
    frontier: list[dict[str, float]] = Field(default_factory=list)


# ==================== Watchlist DTOs ====================

class WatchlistGroupDTO(BaseModel):
    """Watchlist group DTO."""
    id: int = 0
    name: str
    description: str = ""
    color: str = ""
    is_default: bool = False
    stock_count: int = 0
    created_at: datetime | None = None


class WatchlistItemDTO(BaseModel):
    """Watchlist item DTO."""
    symbol: str
    name: str = ""
    market: str = "CN"
    group_id: int = 0

    current_price: float = 0.0
    change_pct: float = 0.0

    added_at: datetime | None = None
    priority: int = 0


# ==================== Risk DTOs ====================

class RiskAssessmentDTO(BaseModel):
    """Risk assessment DTO."""
    portfolio_value: float = 0.0
    risk_level: str = "low"  # low, medium, high, extreme
    risk_score: float = 0.0  # 0-100

    var_95: float = 0.0
    var_99: float = 0.0
    expected_shortfall: float = 0.0
    max_drawdown: float = 0.0
    concentration_risk: float = 0.0
    sector_exposures: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    entangled_risk: dict[str, Any] = Field(default_factory=dict)

    code: str = ""
    score: float = 50.0
    level: str = "medium"
    volatility: float = 0.0
    beta: float = 1.0
    factors: dict[str, float] = Field(default_factory=dict)
    support_levels: list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)

    assessed_at: datetime = Field(default_factory=datetime.now)


class PositionRiskDTO(BaseModel):
    """Position risk DTO."""
    id: str = ""
    code: str
    name: str = ""
    value: float = 0.0
    weight: float = 0.0
    risk_level: str = "low"
    risk_score: float = 0.0
    var_95: float = 0.0
    sector: str = "default"


class RiskAlertDTO(BaseModel):
    """Risk alert DTO."""
    id: str = ""
    code: str
    alert_type: str
    message: str
    severity: str = "low"  # low, medium, high, critical
    created_at: datetime | None = None


class RiskLimitDTO(BaseModel):
    """Risk limit DTO."""
    name: str
    value: float
    description: str = ""


class AlertDTO(BaseModel):
    """Alert/Notification DTO."""
    id: str = ""
    type: str  # risk, price, signal, system
    level: str = "info"  # info, warning, error, critical

    title: str
    message: str

    code: str | None = None
    related_id: str | None = None

    read: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== Task DTOs ====================

class TaskResultDTO(BaseModel):
    """Background task result DTO."""
    task_id: str
    status: str = "pending"  # pending, running, success, failed

    result: Any = None
    error: str | None = None

    progress: float = 0.0  # 0-100
    message: str = ""

    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ==================== Response Wrappers ====================

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    data: Any = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def ok(data: Any = None) -> APIResponse:
        return APIResponse(success=True, data=data)

    @staticmethod
    def error_response(message: str, data: Any = None) -> APIResponse:
        return APIResponse(success=False, error=message, data=data)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False

    @classmethod
    def create(cls, items: list[Any], total: int, page: int = 1, page_size: int = 20) -> PaginatedResponse:
        has_next = (page * page_size) < total
        return cls(items=items, total=total, page=page, page_size=page_size, has_next=has_next)
