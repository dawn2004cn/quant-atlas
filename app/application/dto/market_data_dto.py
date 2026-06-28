from __future__ import annotations
"""DTOs for Market Data services."""


from typing import Any
from pydantic import BaseModel, Field


class MarketSentimentDTO(BaseModel):
    """DTO for market sentiment analysis."""
    regime: str
    recommended_categories: list[str] = Field(default_factory=list)
    benchmark: str
    analysis_at: str
    message: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarketSentimentDTO:
        """Create from dictionary."""
        return cls(**data)


class MarketOverviewDTO(BaseModel):
    """DTO for market overview."""
    market_info: dict[str, Any]
    sentiment: MarketSentimentDTO
    rankings: dict[str, list[dict[str, Any]]]
    server_time: str

    @classmethod
    def from_dicts(
        cls,
        market_info: dict[str, Any],
        sentiment: dict[str, Any],
        rankings: dict[str, list[dict[str, Any]]],
        server_time: str,
    ) -> MarketOverviewDTO:
        """Create from dictionaries."""
        return cls(
            market_info=market_info,
            sentiment=MarketSentimentDTO.from_dict(sentiment),
            rankings=rankings,
            server_time=server_time,
        )


class StockQuoteDTO(BaseModel):
    """DTO for formatted stock quote."""
    code: str
    name: str
    price: float
    change_pct: float
    change_amount: float
    prev_close: float
    volume: int
    amount: float
    turnover: float
    volume_ratio: float
    amplitude: float
    open: float
    high: float
    low: float
    industry: str = ""
    updated_at: str | None = None


class BacktestRequestDTO(BaseModel):
    """DTO for backtest request."""
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    strategy_name: str = Field(default="MA", description="Strategy name")
    start: str = Field(..., description="Start date YYYY-MM-DD")
    end: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: float = Field(default=100000.0, gt=0, description="Initial capital")


class BacktestCompareRequestDTO(BaseModel):
    """DTO for multi-strategy backtest comparison (strategy duel)."""

    symbol: str = Field(..., min_length=1, description="Stock symbol")
    strategies: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Strategy names to compare on the same symbol and period",
    )
    start: str = Field(..., description="Start date YYYY-MM-DD")
    end: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: float = Field(default=100000.0, gt=0, description="Initial capital")


class SelectionRequestDTO(BaseModel):
    """DTO for stock selection request."""
    strategy: str = Field(default="classic", description="Strategy name")
    market: str = Field(default="CN", description="Market code")
    top_n: int = Field(default=20, ge=1, le=500, description="Number of results")


# Re-export from domain to preserve backward-compat imports
from app.domain.dto.market_data_dto import LonghuEntry  # noqa: F401 — re-export only

__all__ = ["LonghuEntry"]  # keep module importable


class YanbaoEntry(BaseModel):
    """Representing a research report entry."""
    category: str
    title: str
    org_name: str
    pub_date: str
    stock_code: str
    report_url: str
    raw: dict[str, Any] = Field(default_factory=dict)


class FinancialStashDTO(BaseModel):
    """Representing financial statement snapshots."""
    code: str
    payload: dict[str, Any]
    updated_at: str


class StockDetailDTO(BaseModel):
    """DTO for stock detail with profile, history, indicators and news."""
    symbol: str
    market: str
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    indicators: dict[str, Any] = Field(default_factory=dict)
    news: list[dict[str, Any]] = Field(default_factory=list)
    industry_news: list[dict[str, Any]] = Field(default_factory=list)


class NewsSnapshotDTO(BaseModel):
    """DTO for lightweight news snapshot (profile + news only)."""
    symbol: str
    market: str
    news: list[dict[str, Any]] = Field(default_factory=list)
    industry_news: list[dict[str, Any]] = Field(default_factory=list)
    company_name_hint: str = ""
    industry_hint: str = ""


class StockHistoryDTO(BaseModel):
    """DTO for stock history with OHLCV and indicators."""
    symbol: str
    market: str
    start: str
    end: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    indicators: dict[str, Any] = Field(default_factory=dict)


class MarketSentimentMetricsDTO(BaseModel):
    """DTO for market sentiment metrics."""
    score: float
    up_count: int
    down_count: int
    flat_count: int
    stats: dict[str, Any]
    emoji: str = ""
    level: str = ""
    description: str = ""
    update_time: str


class StockMovementDTO(BaseModel):
    """DTO for stock movement/alert."""
    code: str
    name: str
    type: str
    change: str
    time: str
    price: float = 0
