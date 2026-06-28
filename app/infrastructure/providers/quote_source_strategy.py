from __future__ import annotations
"""Quote Source Strategy - Extensible data source pattern.

This module provides a strategy pattern for adding quote data sources
without modifying the main MultiSourceMarketProvider class.
"""


from abc import ABC, abstractmethod

from app.domain.entities import StockQuote
from app.domain.enums import MarketCode


class QuoteSourceStrategy(ABC):
    """Abstract base class for quote data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the source name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is available."""
        pass

    @abstractmethod
    def fetch_quotes(
        self,
        symbols: list[str],
        market: MarketCode,
    ) -> list[StockQuote]:
        """Fetch quotes for given symbols."""
        pass


class QuoteSourceRegistry:
    """Registry for quote source strategies."""

    _sources: list[QuoteSourceStrategy] = []

    @classmethod
    def register(cls, source: QuoteSourceStrategy) -> None:
        """Register a new quote source."""
        cls._sources.append(source)

    @classmethod
    def get_sources(cls) -> list[QuoteSourceStrategy]:
        """Get all registered sources."""
        return list(cls._sources)

    @classmethod
    def get_available_sources(cls) -> list[QuoteSourceStrategy]:
        """Get available sources (those that return True for is_available)."""
        return [s for s in cls._sources if s.is_available()]


def register_standard_sources() -> None:
    """Register standard quote sources.

    This is called during app initialization to register
    the default set of quote sources.
    """
    from app.infrastructure.providers.market_data import MultiSourceMarketProvider

    class MarketProviderSource(QuoteSourceStrategy):
        @property
        def name(self) -> str:
            return "multi_source_market"

        def is_available(self) -> bool:
            return True

        def fetch_quotes(
            self,
            symbols: list[str],
            market: MarketCode,
        ) -> list[StockQuote]:
            provider = MultiSourceMarketProvider()
            return provider.get_realtime_quotes(symbols, market)

    QuoteSourceRegistry.register(MarketProviderSource())
