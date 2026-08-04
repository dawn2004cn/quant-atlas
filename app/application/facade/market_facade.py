from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.application.errors import ValidationError
from app.domain.enums import MarketCode
from app.application.facade._helpers import observe_facade, parse_market, validation_error_from_pydantic
from app.application.facade.dto.market_facade_dto import (
    HistoryBarsQueryDTO,
    MarketPanoramaDTO,
    MarketQuotesQueryDTO,
)


class MarketFacade:
    """High-level facade for market-related services.

    Provides a stable API for Web routes, Celery tasks, and CLI entry points.
    """

    _FACADE_NAME = "market"

    def __init__(
        self,
        stock_service: Any,
        market_service: Any,
        watchlist_service: Any | None = None,
        market_data_provider: Any | None = None,
        indicator_provider: Any | None = None,
    ):
        self.stock_service = stock_service
        self.market_service = market_service
        self.watchlist_service = watchlist_service
        self.market_data_provider = market_data_provider
        self.indicator_provider = indicator_provider

    @staticmethod
    def _parse_market(market: str | MarketCode) -> MarketCode:
        return parse_market(market)

    def get_panorama(self, market: str | MarketCode) -> dict[str, Any]:
        """Return market panorama as a plain dict for API serialization."""
        with observe_facade(self._FACADE_NAME, "get_panorama"):
            mc = self._parse_market(market)
            svc = self.market_service if self.market_service is not None else self.stock_service
            panorama = svc.get_panorama(mc)
            return MarketPanoramaDTO.from_service(panorama, market=mc.value).model_dump()

    def get_stock(self, symbol: str):
        """Retrieve stock information for a given symbol."""
        with observe_facade(self._FACADE_NAME, "get_stock"):
            try:
                query = HistoryBarsQueryDTO(symbol=symbol, market="CN", count=1)
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc
            return self.stock_service.get_stock(query.symbol)

    def get_watchlist(self, name: str):
        """Retrieve watchlist by name."""
        with observe_facade(self._FACADE_NAME, "get_watchlist"):
            if self.watchlist_service is None:
                raise ValidationError("Watchlist service not configured")
            if not (name or "").strip():
                raise ValidationError("watchlist name is required")
            return self.watchlist_service.get_watchlist(name.strip())

    def get_indicator(self, indicator_name: str, *args: Any, **kwargs: Any):
        """Fetch indicator data via the provider."""
        with observe_facade(self._FACADE_NAME, "get_indicator"):
            provider = self.indicator_provider
            if provider is None:
                raise ValidationError("Indicator provider not configured")
            if not (indicator_name or "").strip():
                raise ValidationError("indicator_name is required")
            return provider.get_indicator(indicator_name, *args, **kwargs)

    def list_quotes(self, market: str, symbols: list[str] | None = None):
        """Delegate to stock_service.list_quotes for market quotes."""
        with observe_facade(self._FACADE_NAME, "list_quotes"):
            try:
                query = MarketQuotesQueryDTO(market=market, symbols=symbols)
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc
            mc = self._parse_market(query.market)
            return self.stock_service.list_quotes(mc.value, query.symbols)

    def get_history(self, symbol: str, market: Any, start: str, end: str):
        """Delegate to stock_service.get_history for historical data."""
        with observe_facade(self._FACADE_NAME, "get_history"):
            query = self._build_history_query(
                symbol=symbol,
                market=market,
                start_date=start,
                end_date=end,
            )
            mc = self._parse_market(query.market)
            return self.stock_service.get_history(query.symbol, mc, query.start_date or "", query.end_date or "")

    def get_sentiment(self, market: str):
        """Delegate to stock_service.get_sentiment for market sentiment."""
        with observe_facade(self._FACADE_NAME, "get_sentiment"):
            mc = self._parse_market(market)
            return self.stock_service.get_sentiment(mc.value)

    def get_history_bars(
        self,
        *,
        symbol: str,
        market: str | MarketCode,
        start_date: str | None = None,
        end_date: str | None = None,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """Return historical bars via market_service (with get_history fallback)."""
        with observe_facade(self._FACADE_NAME, "get_history_bars"):
            query = self._build_history_query(
                symbol=symbol,
                market=market,
                start_date=start_date,
                end_date=end_date,
                count=count,
            )
            mc = self._parse_market(query.market)
            svc = self.market_service
            if svc is None:
                raise ValidationError("Market service not configured")

            if hasattr(svc, "get_history_bars"):
                return svc.get_history_bars(
                    symbol=query.symbol,
                    market=mc,
                    start_date=query.start_date,
                    end_date=query.end_date,
                    count=query.count,
                )

            start = query.start_date or ""
            end = query.end_date or ""
            if hasattr(svc, "get_history"):
                bars = svc.get_history(query.symbol, mc, start=start, end=end)
                if query.count and len(bars) > query.count:
                    return bars[-query.count :]
                return bars

            raise ValidationError("History API not configured on market service")

    def _build_history_query(
        self,
        *,
        symbol: str,
        market: str | MarketCode,
        start_date: str | None = None,
        end_date: str | None = None,
        count: int = 100,
    ) -> HistoryBarsQueryDTO:
        market_value = market.value if isinstance(market, MarketCode) else str(market)
        try:
            return HistoryBarsQueryDTO(
                symbol=symbol,
                market=market_value,
                start_date=start_date,
                end_date=end_date,
                count=count,
            )
        except PydanticValidationError as exc:
            raise validation_error_from_pydantic(exc) from exc
