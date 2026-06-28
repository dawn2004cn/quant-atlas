from __future__ import annotations

"""Complete DTO contracts with strict type validation.

This module provides comprehensive DTOs with Pydantic validation,
replacing dict-based data transfer throughout the codebase.
"""


from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

# ==================== Enums ====================

class Market(str, Enum):
    """Market code."""
    CN = "CN"
    HK = "HK"
    US = "US"


class SignalDirection(str, Enum):
    """Signal direction."""
    LONG = "long"
    SHORT = "short"
    BUY = "buy"
    SELL = "sell"


class SignalStrength(str, Enum):
    """Signal strength."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class PositionStatus(str, Enum):
    """Position status."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """Risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


# ==================== Market DTOs ====================

class BarContract(BaseModel):
    """OHLCV bar data contract with strict validation."""
    date: str = Field(description="Trade date")
    open: float = Field(gt=0, description="Open price")
    high: float = Field(gt=0, description="High price")
    low: float = Field(gt=0, description="Low price")
    close: float = Field(gt=0, description="Close price")
    volume: int = Field(ge=0, description="Volume")
    amount: float | None = Field(default=None, ge=0, description="Amount")

    @model_validator(mode="after")
    def validate_price_relationship(self):
        if self.high < self.low:
            raise ValueError("High price must be >= Low price")
        if self.open > self.high or self.open < self.low:
            raise ValueError("Open price must be within high-low range")
        if self.close > self.high or self.close < self.low:
            raise ValueError("Close price must be within high-low range")
        return self


class QuoteContract(BaseModel):
    """Real-time quote contract."""
    code: str = Field(min_length=6, max_length=8, description="Stock code")
    name: str = Field(default="", description="Stock name")
    price: float = Field(gt=0, description="Current price")
    change: float = Field(description="Price change")
    change_pct: float = Field(description="Change percentage")
    volume: int = Field(ge=0, description="Volume")
    amount: float = Field(ge=0, description="Amount")
    high: float = Field(gt=0, description="High price")
    low: float = Field(gt=0, description="Low price")
    open: float = Field(gt=0, description="Open price")
    prev_close: float = Field(gt=0, description="Previous close")
    bid: float = Field(gt=0, description="Bid price")
    ask: float = Field(gt=0, description="Ask price")
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def spread(self) -> float:
        return round(self.ask - self.bid, 4)

    @computed_field
    @property
    def is_up(self) -> bool:
        return self.change > 0


# ==================== Strategy DTOs ====================

class StrategySignalContract(BaseModel):
    """Trading signal contract."""
    code: str = Field(min_length=6, max_length=8)
    name: str = ""
    signal_type: str = Field(description="Signal type: breakout, momentum, etc.")
    direction: SignalDirection = SignalDirection.LONG
    strength: SignalStrength = SignalStrength.MODERATE
    price: float = Field(gt=0)
    target_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    confidence: float = Field(ge=0, le=100, description="Confidence 0-100")
    reason: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None

    @computed_field
    @property
    def risk_reward(self) -> float | None:
        if not all([self.target_price, self.stop_loss, self.price]):
            return None
        reward = abs(self.target_price - self.price)
        risk = abs(self.price - self.stop_loss)
        return round(reward / risk, 2) if risk > 0 else None


class StrategyResultContract(BaseModel):
    """Strategy execution result contract."""
    strategy_name: str
    signals: list[StrategySignalContract] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== Portfolio DTOs ====================

class PositionContract(BaseModel):
    """Position contract."""
    id: str = ""
    code: str = Field(min_length=6, max_length=8)
    name: str = ""
    side: SignalDirection = SignalDirection.LONG
    quantity: int = Field(gt=0)
    avg_cost: float = Field(gt=0)
    current_price: float = Field(gt=0)
    opened_at: datetime
    closed_at: datetime | None = None
    status: PositionStatus = PositionStatus.OPEN
    tags: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def total_cost(self) -> float:
        return self.quantity * self.avg_cost

    @computed_field
    @property
    def total_value(self) -> float:
        return self.quantity * self.current_price

    @computed_field
    @property
    def pnl(self) -> float:
        if self.side == SignalDirection.LONG:
            return self.total_value - self.total_cost
        return self.total_cost - self.total_value

    @computed_field
    @property
    def pnl_pct(self) -> float:
        if self.total_cost == 0:
            return 0
        return round(self.pnl / self.total_cost * 100, 2)


class PortfolioContract(BaseModel):
    """Portfolio contract."""
    id: str
    name: str = "Default Portfolio"
    initial_capital: float = Field(gt=0)
    current_capital: float = Field(gt=0)
    cash: float = Field(ge=0)
    positions: list[PositionContract] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def total_value(self) -> float:
        return self.cash + sum(p.total_value for p in self.positions)

    @computed_field
    @property
    def total_pnl(self) -> float:
        return sum(p.pnl for p in self.positions)


# ==================== Risk DTOs ====================

class RiskAssessmentContract(BaseModel):
    """Risk assessment contract."""
    code: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: float = Field(ge=0, le=100)
    var_95: float = Field(description="Value at Risk 95%")
    var_99: float = Field(description="Value at Risk 99%")
    expected_shortfall: float = Field(description="Expected Shortfall")
    max_drawdown: float = Field(ge=0)
    beta: float = Field(default=1.0)
    volatility: float = Field(ge=0)
    concentration_risk: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.now)


class RiskLimitContract(BaseModel):
    """Risk limit contract."""
    name: str
    value: float
    description: str = ""
    enabled: bool = True


# ==================== Order DTOs ====================

class OrderContract(BaseModel):
    """Order contract."""
    id: str = ""
    code: str = Field(min_length=6, max_length=8)
    name: str = ""
    direction: SignalDirection
    order_type: str = Field(description="market, limit")
    quantity: int = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    filled_quantity: int = Field(default=0, ge=0)
    filled_price: float = Field(default=0, ge=0)
    status: OrderStatus = OrderStatus.PENDING
    order_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    filled_at: datetime | None = None

    @computed_field
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @computed_field
    @property
    def fill_rate(self) -> float:
        if self.quantity == 0:
            return 0
        return round(self.filled_quantity / self.quantity * 100, 2)


# ==================== Analysis DTOs ====================

class TechnicalIndicatorContract(BaseModel):
    """Technical indicators contract."""
    code: str
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    rsi: float = Field(default=50.0, ge=0, le=100)
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    kdj_k: float = Field(default=50.0, ge=0, le=100)
    kdj_d: float = Field(default=50.0, ge=0, le=100)
    kdj_j: float = Field(default=50.0, ge=0, le=100)
    boll_upper: float = 0.0
    boll_middle: float = 0.0
    boll_lower: float = 0.0
    atr: float = 0.0


class AnalysisResultContract(BaseModel):
    """Analysis result contract."""
    code: str
    name: str = ""
    price: float = Field(gt=0)
    trend: str = Field(description="up, down, sideways")
    momentum: float = Field(ge=-100, le=100)
    indicators: TechnicalIndicatorContract | None = None
    support_levels: list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=100)
    recommendation: str = Field(description="strong_buy, buy, hold, sell, strong_sell")
    analyzed_at: datetime = Field(default_factory=datetime.now)


# ==================== Pipeline DTOs ====================

class PipelineConfigContract(BaseModel):
    """Pipeline configuration contract."""
    name: str
    stages: list[str] = Field(description="Reader, Validator, Transformer, Writer")
    enabled: bool = True
    timeout_seconds: int = Field(default=300, gt=0)
    retry_count: int = Field(default=3, ge=0)


class PipelineResultContract(BaseModel):
    """Pipeline execution result contract."""
    pipeline_name: str
    success: bool
    processed_count: int = 0
    error_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== Task DTOs ====================

class TaskContract(BaseModel):
    """Task contract."""
    id: str
    name: str
    priority: str = Field(description="HIGH, MEDIUM, LOW")
    status: str = Field(description="pending, running, completed, failed")
    result: Any | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ==================== Event DTOs ====================

class EventContract(BaseModel):
    """Event contract."""
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


__all__ = [
    # Enums
    "Market", "SignalDirection", "SignalStrength", "PositionStatus",
    "OrderStatus", "RiskLevel",
    # Market
    "BarContract", "QuoteContract",
    # Strategy
    "StrategySignalContract", "StrategyResultContract",
    # Portfolio
    "PositionContract", "PortfolioContract",
    # Risk
    "RiskAssessmentContract", "RiskLimitContract",
    # Order
    "OrderContract",
    # Analysis
    "TechnicalIndicatorContract", "AnalysisResultContract",
    # Pipeline
    "PipelineConfigContract", "PipelineResultContract",
    # Task
    "TaskContract",
    # Event
    "EventContract",
    # Re-export common types
    "BaseModel",
    "Field",
    "field_validator",
    "model_validator",
    "computed_field",
    "datetime",
    "Optional",
    "Any",
]
