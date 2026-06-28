from __future__ import annotations
"""Market data ports - interfaces for data access layer."""


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from ..enums import MarketCode
from ..entities import ChipDistribution, StockQuote


class MarketOverviewPort(ABC):
    """Port for market overview and rankings."""

    @abstractmethod
    def get_market_overview(self, market: MarketCode) -> dict[str, Any]:
        """Get market overview (indices, sector performance)."""
        raise NotImplementedError

    @abstractmethod
    def get_market_rankings(self, market: MarketCode) -> dict[str, list[dict[str, Any]]]:
        """Get market rankings (top gainers, losers, volume)."""
        raise NotImplementedError


class QuotePort(ABC):
    """Port for real-time quotes and stock profiles."""

    @abstractmethod
    def get_realtime_quotes(self, symbols: list[str] | None = None, market: MarketCode = MarketCode.CN) -> list[StockQuote]:
        """Get real-time quotes for symbols."""
        raise NotImplementedError

    @abstractmethod
    def get_stock_profile(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        """Get stock profile/company info."""
        raise NotImplementedError


class HistoryPort(ABC):
    """Port for historical OHLCV data."""

    @abstractmethod
    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Get historical OHLCV data."""
        raise NotImplementedError


class ChipDataPort(ABC):
    """Port for chip distribution data."""

    @abstractmethod
    def get_chip_distribution(self, symbol: str, market: MarketCode) -> ChipDistribution | None:
        """Get chip distribution data."""
        raise NotImplementedError


class MarketDataProvider(MarketOverviewPort, QuotePort, HistoryPort, ChipDataPort):
    """Port for market data providers (combines all market data interfaces)."""
    pass


class NewsProvider(ABC):
    """Port for news data providers."""

    @abstractmethod
    def get_stock_news(self, symbol: str, market: MarketCode) -> list[dict[str, Any]]:
        """Get news items for a stock."""
        raise NotImplementedError

    def get_industry_news(self, industry: str, market: MarketCode) -> list[dict[str, Any]]:
        """Get news items for an industry. Returns empty list by default."""
        return []


class WebSearchProvider(ABC):
    """Port for web search providers."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Perform web search."""
        raise NotImplementedError


class SentimentProvider(ABC):
    """Port for sentiment analysis providers."""

    @abstractmethod
    def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Analyze sentiment of text."""
        raise NotImplementedError


class FinGPTPersistencePort(ABC):
    """Port for FinGPT persistence."""

    @abstractmethod
    def save_prediction(self, prediction: dict[str, Any]) -> str:
        """Save prediction and return ID."""
        raise NotImplementedError

    @abstractmethod
    def list_predictions(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent predictions."""
        raise NotImplementedError

    @abstractmethod
    def save_sentiment(self, ticker: str, data: dict[str, Any]) -> bool:
        """Save sentiment data."""
        raise NotImplementedError


class IndicatorProvider(ABC):
    """Port for technical indicator calculation."""

    @abstractmethod
    def calculate(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate technical indicators from OHLCV data."""
        raise NotImplementedError


class IndustryProvider(ABC):
    """Port for industry classification data."""

    @abstractmethod
    def get_industry_map(self, allow_fetch: bool = True) -> dict[str, str]:
        """Get industry mapping for stocks (code6 -> industry name)."""
        raise NotImplementedError
