from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Market data aggregator using domain models and events."""


from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.dto.complete_dto import QuoteDTO
from app.application.events import EventType, publish_event
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedQuote:
    """Aggregated quote from multiple sources."""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    source: str
    timestamp: datetime


class MarketDataAggregator:
    """Aggregates market data from multiple providers."""

    def __init__(self):
        self._quotes: dict[str, AggregatedQuote] = {}
        self._sources: dict[str, object] = {}
        logger.info("MarketDataAggregator initialized")

    def register_source(self, name: str, provider: object):
        """Register a data source provider."""
        self._sources[name] = provider
        logger.info(f"Registered data source: {name}")

    async def fetch_quote(self, code: str) -> QuoteDTO | None:
        """Fetch quote from all registered sources and aggregate."""
        quotes = []

        for source_name, provider in self._sources.items():
            try:
                if hasattr(provider, 'get_quote'):
                    quote = await provider.get_quote(code)
                    if quote:
                        quotes.append((source_name, quote))
                elif hasattr(provider, 'get_real_time_quote'):
                    quote = provider.get_real_time_quote(code)
                    if quote:
                        quotes.append((source_name, quote))
            except Exception as e:
                logger.warning(f"Failed to get quote from {source_name}: {e}")

        if not quotes:
            return None

        best_quote = self._choose_best_quote(quotes)

        aggregated = AggregatedQuote(
            code=code,
            name=best_quote.get("name", ""),
            price=best_quote.get("price", 0),
            change=best_quote.get("change", 0),
            change_pct=best_quote.get("change_pct", 0),
            volume=best_quote.get("volume", 0),
            source=best_quote[0] if isinstance(best_quote, tuple) else "unknown",
            timestamp=datetime.now(),
        )
        self._quotes[code] = aggregated

        await publish_event(
            EventType.QUOTE_UPDATED,
            {"code": code, "price": aggregated.price, "source": aggregated.source},
            source="MarketDataAggregator"
        )

        return QuoteDTO(
            code=aggregated.code,
            name=aggregated.name,
            price=aggregated.price,
            change=aggregated.change,
            change_pct=aggregated.change_pct,
            volume=aggregated.volume,
            timestamp=aggregated.timestamp,
        )

    def _choose_best_quote(self, quotes: list) -> Any:
        """Choose the best quote based on freshness and completeness."""
        scored = []
        for source, quote in quotes:
            score = 0
            if quote.get("price"):
                score += 10
            if quote.get("volume", 0) > 0:
                score += 5
            if quote.get("change_pct") is not None:
                score += 3
            scored.append((score, source, quote))

        scored.sort(reverse=True)
        return scored[0][2] if scored else {}

    async def fetch_batch(self, codes: list[str]) -> list[QuoteDTO]:
        """Fetch quotes for multiple codes."""
        results = []
        for code in codes:
            quote = await self.fetch_quote(code)
            if quote:
                results.append(quote)
        return results

    def get_cached_quote(self, code: str) -> QuoteDTO | None:
        """Get cached quote."""
        agg = self._quotes.get(code)
        if not agg:
            return None
        return QuoteDTO(
            code=agg.code,
            name=agg.name,
            price=agg.price,
            change=agg.change,
            change_pct=agg.change_pct,
            volume=agg.volume,
            timestamp=agg.timestamp,
        )

    def clear_cache(self):
        """Clear cached quotes."""
        self._quotes.clear()

    def get_source_status(self) -> GenericResponseDTO[str, object]:
        """Get status of all registered sources."""
        return {
            name: "active" if hasattr(provider, 'get_quote') else "unknown"
            for name, provider in self._sources.items()
        }


_aggregator: MarketDataAggregator | None = None


def get_market_aggregator() -> MarketDataAggregator:
    """Get global market data aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = MarketDataAggregator()
    return _aggregator


__all__ = ["MarketDataAggregator", "get_market_aggregator", "AggregatedQuote"]
