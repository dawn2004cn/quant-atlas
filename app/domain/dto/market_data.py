from __future__ import annotations

"""Market data DTOs with strict type contracts."""


from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BarData(BaseModel):
    """OHLCV bar data with strict type contract."""
    date: str
    open: float = Field(gt=0, description="Open price")
    high: float = Field(gt=0, description="High price")
    low: float = Field(gt=0, description="Low price")
    close: float = Field(gt=0, description="Close price")
    volume: int = Field(ge=0, description="Trading volume")

    amount: float | None = Field(default=None, description="Trading amount")
    turnover: float | None = Field(default=None, description="Turnover rate")

    @field_validator("high")
    @classmethod
    def validate_high(cls, v, info):
        if "data" in info and info["data"]:
            data = info["data"]
            if "open" in data and v < data["open"]:
                raise ValueError("High must be >= Open")
            if "close" in data and v < data["close"]:
                raise ValueError("High must be >= Close")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v, info):
        if "data" in info and info["data"]:
            data = info["data"]
            if "open" in data and v > data["open"]:
                raise ValueError("Low must be <= Open")
            if "close" in data and v > data["close"]:
                raise ValueError("Low must be <= Close")
        return v

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class QuoteData(BaseModel):
    """Real-time quote data with strict type contract."""
    code: str = Field(min_length=6, max_length=8)
    name: str = Field(default="")

    price: float = Field(gt=0)
    change: float = Field(description="Price change")
    change_pct: float = Field(description="Price change percentage")

    volume: int = Field(ge=0)
    amount: float = Field(ge=0)

    bid: float = Field(gt=0, description="Bid price")
    ask: float = Field(gt=0, description="Ask price")

    high: float = Field(gt=0)
    low: float = Field(gt=0)
    open: float = Field(gt=0)
    prev_close: float = Field(gt=0)

    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_up(self) -> bool:
        return self.change > 0

    @property
    def is_down(self) -> bool:
        return self.change < 0

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2


class TickData(BaseModel):
    """Tick-by-tick data with strict type contract."""
    code: str
    timestamp: datetime

    price: float = Field(gt=0)
    volume: int = Field(ge=0)

    bid: float = Field(gt=0)
    ask: float = Field(gt=0)

    direction: str | None = Field(default=None, description="buy or sell")


class StockProfile(BaseModel):
    """Stock profile data."""
    code: str
    name: str

    industry: str = ""
    sector: str = ""
    market: str = "CN"

    listing_date: str | None = None
    delist_date: str | None = None

    total_shares: float | None = None
    circulating_shares: float | None = None

    @property
    def is_listed(self) -> bool:
        return self.delist_date is None


class MarketStats(BaseModel):
    """Market statistics data."""
    market: str

    total_stocks: int = 0
    trading_stocks: int = 0

    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0

    total_volume: int = 0
    total_amount: float = 0

    index_value: float = 0
    index_change: float = 0
    index_change_pct: float = 0

    @property
    def up_ratio(self) -> float:
        if self.total_stocks == 0:
            return 0
        return self.up_count / self.total_stocks


class SignalData(BaseModel):
    """Trading signal data."""
    code: str
    name: str = ""

    signal_type: str
    direction: str = "long"
    strength: str = "moderate"

    price: float = Field(gt=0)
    confidence: float = Field(ge=0, le=100)

    target_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)

    reason: str = ""

    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None


class PositionData(BaseModel):
    """Position data."""
    code: str
    name: str = ""

    side: str = "long"

    quantity: int = Field(gt=0)
    avg_cost: float = Field(gt=0)
    current_price: float = Field(gt=0)

    opened_at: datetime
    closed_at: datetime | None = None

    status: str = "open"

    tags: list[str] = Field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return self.quantity * self.avg_cost

    @property
    def total_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def pnl(self) -> float:
        if self.side == "long":
            return self.total_value - self.total_cost
        return self.total_cost - self.total_value


class RiskAssessmentData(BaseModel):
    """Risk assessment data."""
    code: str

    risk_level: str = "medium"
    risk_score: float = Field(ge=0, le=100)

    var_95: float = Field(description="Value at Risk 95%")
    var_99: float = Field(description="Value at Risk 99%")

    beta: float = Field(default=1.0)
    volatility: float = Field(ge=0)

    max_drawdown: float = Field(ge=0)

    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "BarData",
    "QuoteData",
    "TickData",
    "StockProfile",
    "MarketStats",
    "SignalData",
    "PositionData",
    "RiskAssessmentData",
    "LonghuDTO",
]

class LonghuDTO(BaseModel):
    trade_date: str
    code: str
    name: str
    reason: str
    raw: dict[str, Any]
