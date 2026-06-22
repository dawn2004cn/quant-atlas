"""Market Data Service port adapter.

Bridges the current monolithic implementation to the MarketDataServicePort
interface. This adapter will become the HTTP server in Phase 2A.
"""

from __future__ import annotations

from typing import Any

from app.modules.market_data.api_contract import MarketDataServicePort


class MonolithMarketDataAdapter(MarketDataServicePort):
    """Adapter that wraps existing monolith services to implement the port.

    This class delegates to the current Flask-based services but presents
    a clean interface that can be backed by an independent HTTP service
    in Phase 2A.
    """

    def __init__(
        self,
        market_service: Any | None = None,
        stock_service: Any | None = None,
        global_market_service: Any | None = None,
        basic_market_data_service: Any | None = None,
        hot_sector_service: Any | None = None,
        sentiment_radar: Any | None = None,
    ) -> None:
        self._market_service = market_service
        self._stock_service = stock_service
        self._global_market_service = global_market_service
        self._basic_market_data = basic_market_data_service
        self._hot_sector = hot_sector_service
        self._sentiment = sentiment_radar

    def get_quote(self, symbol: str, market: str) -> dict[str, Any]:
        if self._market_service is None:
            raise RuntimeError("market_service not available")
        return self._market_service.get_quote(symbol, market)

    def get_quotes(self, symbols: list[str], market: str) -> list[dict[str, Any]]:
        if self._market_service is None:
            raise RuntimeError("market_service not available")
        return self._market_service.get_quotes(symbols, market)

    def get_history(self, symbol: str, market: str, start: str, end: str) -> dict[str, Any]:
        if self._stock_service is None:
            raise RuntimeError("stock_service not available")
        return self._stock_service.get_history(symbol, market, start, end)

    def get_sector_members(self, sector: str, market: str) -> list[dict[str, Any]]:
        if self._market_service is None:
            raise RuntimeError("market_service not available")
        return self._market_service.get_sector_members(sector, market)

    def get_hot_sectors(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._hot_sector is None:
            return []
        return self._hot_sector.get_hot_sectors(limit=limit)

    def get_sentiment(self, symbols: list[str]) -> dict[str, Any]:
        if self._sentiment is None:
            return {}
        return self._sentiment.get_sentiment(symbols)

    def get_global_quote(self, symbol: str, market: str) -> dict[str, Any]:
        if self._global_market_service is None:
            raise RuntimeError("global_market_service not available")
        return self._global_market_service.get_global_quote(symbol, market)

    def get_fundamental(self, symbol: str, market: str) -> dict[str, Any]:
        if self._stock_service is None:
            raise RuntimeError("stock_service not available")
        return self._stock_service.get_fundamental(symbol, market)


def create_market_data_adapter(registry: Any | None = None) -> MarketDataServicePort:
    """Factory: create MonolithMarketDataAdapter from registry or current services.

    Args:
        registry: Optional TypedServiceRegistry. If provided, services are
                  resolved from registry. If None, creates a no-op adapter.

    Returns:
        MarketDataServicePort implementation.
    """
    if registry is None:
        return MonolithMarketDataAdapter()

    return MonolithMarketDataAdapter(
        market_service=registry.get_or_none("market_service"),
        stock_service=registry.get_or_none("stock_service"),
        global_market_service=registry.get_or_none("global_market_service"),
        basic_market_data_service=registry.get_or_none("basic_market_data_service"),
        hot_sector_service=registry.get_or_none("hot_sector_service"),
        sentiment_radar=registry.get_or_none("sentiment_radar"),
    )
