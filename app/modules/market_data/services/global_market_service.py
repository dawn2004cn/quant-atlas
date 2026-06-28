from __future__ import annotations
"""Application service for global market data (OpenBB port)."""


from datetime import datetime, timedelta
from typing import Any

from app.domain.ports import MarketDataProvider, OpenBBRepository
from app.domain.market_entities import ProviderConfig
from app.domain.enums import MarketCode
from app.domain.dto import GlobalQuoteDTO, GlobalHistoryDTO, GlobalMarketConfigDTO


from app.core.logger import get_logger

logger = get_logger(__name__)


class GlobalMarketService:
    def __init__(self, provider: MarketDataProvider, repository: OpenBBRepository):
        self._provider = provider
        self._repository = repository

    def get_global_quote(self, symbol: str, market: MarketCode) -> GlobalQuoteDTO:
        """Fetch global quote with caching."""
        try:
            cached = self._repository.get_cached_data("openbb", symbol, "quote")
            if cached:
                return GlobalQuoteDTO.model_validate(cached)

            quotes = self._provider.get_realtime_quotes(symbols=[symbol], market=market)
            if quotes:
                q = quotes[0]
                result = GlobalQuoteDTO(
                    symbol=q.code,
                    name=q.name,
                    price=q.price,
                    change=q.change_amount,
                    change_pct=q.change_pct,
                    volume=q.volume,
                    source="openbb",
                    last_updated=datetime.now().isoformat(),
                )
                self._repository.cache_data("openbb", symbol, "quote", result.model_dump(), ttl_hours=0.08)
                return result
        except Exception as e:
            logger.warning(f"Failed to fetch global quote for {symbol}: {e}")

        return GlobalQuoteDTO(symbol=symbol, name=symbol)

    def get_global_history(self, symbol: str, market: MarketCode, days: int = 30) -> GlobalHistoryDTO:
        """Fetch global history with caching."""
        try:
            timeframe = f"{days}d"
            cached = self._repository.get_cached_data("openbb", symbol, "historical", timeframe=timeframe)
            if cached:
                return GlobalHistoryDTO.model_validate(cached)

            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            history = self._provider.get_stock_history(symbol, market, start, end)
            if history:
                result = GlobalHistoryDTO(
                    symbol=symbol,
                    market=market.value,
                    history=history,
                    count=len(history),
                )
                self._repository.cache_data("openbb", symbol, "historical", result.model_dump(), timeframe=timeframe, ttl_hours=24)
                return result
        except Exception as e:
            logger.warning(f"Failed to fetch global history for {symbol}: {e}")

        return GlobalHistoryDTO(symbol=symbol, market=market.value)

    def configure_provider(self, provider_name: str, settings: dict[str, Any]) -> GlobalMarketConfigDTO:
        config = ProviderConfig(provider_name=provider_name, settings=settings)
        self._repository.save_provider_config(config)
        return GlobalMarketConfigDTO(provider_name=provider_name, settings=settings)
