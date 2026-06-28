from __future__ import annotations
"""Standardized Bar data contract."""


from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BarData(BaseModel):
    """Immutable OHLCV bar data contract."""

    code: str = Field(..., description="Stock code, e.g. '000001'")
    name: str = Field(default="", description="Stock name")
    trade_date: str = Field(..., description="Trading date, format: YYYY-MM-DD")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(0.0, description="Trading volume (shares)")
    amount: float = Field(0.0, description="Trading amount (CNY)")
    turnover: float = Field(0.0, description="Turnover rate (%)")
    change_pct: float = Field(0.0, description="Price change percentage")

    @property
    def is_valid(self) -> bool:
        """Check if bar data is valid."""
        return self.close > 0 and self.high >= self.low

    @property
    def typical_price(self) -> float:
        """Typical price = (high + low + close) / 3"""
        return (self.high + self.low + self.close) / 3


class QuoteData(BaseModel):
    """Real-time quote data contract."""

    code: str
    name: str = ""
    price: float = 0.0
    change_amount: float = 0.0
    change_pct: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    turnover: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    pe: float | None = None
    pb: float | None = None
    market_cap: float | None = None
    industry: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class IndicatorResult(BaseModel):
    """Technical indicator result contract."""

    code: str
    indicator_name: str
    value: float
    signal: Literal["bullish", "bearish", "neutral"] = "neutral"
    strength: float = Field(0.0, ge=0.0, le=1.0, description="Signal strength 0-1")
    meta: dict = Field(default_factory=dict)


class HistoryData(BaseModel):
    """History data container with metadata."""

    code: str
    bars: list[BarData] = Field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    count: int = 0

    @property
    def closes(self) -> list[float]:
        return [b.close for b in self.bars]

    @property
    def highs(self) -> list[float]:
        return [b.high for b in self.bars]

    @property
    def lows(self) -> list[float]:
        return [b.low for b in self.bars]
