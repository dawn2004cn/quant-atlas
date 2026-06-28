from __future__ import annotations

"""Portfolio Market Service - wraps market provider for portfolio operations."""


from typing import Any

from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode
from app.domain.ports.market_ports import MarketDataProvider
from app.modules.system.services.helpers.market_data_provider import get_market_data_provider


class PortfolioMarketService(BaseApplicationService):
    """Service for portfolio-related market data operations."""

    def __init__(self, market_provider: MarketDataProvider | None = None) -> None:
        super().__init__()
        self._provider: MarketDataProvider | None = market_provider
        self._init_provider()

    def _init_provider(self) -> None:
        if self._provider is None:
            try:
                self._provider = get_market_data_provider()
            except RuntimeError as exc:
                self.logger.warning("PortfolioMarketService init failed: %s", exc)
                self._provider = None
                return
        try:
            test_quotes = self._provider.get_realtime_quotes(["600519"], market=MarketCode.CN)
            self.logger.info("PortfolioMarketService initialized, test quote: %s", test_quotes)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, ConnectionError, TimeoutError) as e:
            self.logger.warning("PortfolioMarketService provider probe failed: %s", e)

    def is_available(self) -> bool:
        return self._provider is not None

    def get_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> list[Any]:
        if self._provider is None:
            return []
        try:
            return self._provider.get_realtime_quotes(symbols, market)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, ConnectionError, TimeoutError) as e:
            self.logger.error("get_quotes failed: %s", e)
            return []

    def get_quote(self, symbol: str, market: MarketCode = MarketCode.CN) -> Any | None:
        quotes = self.get_quotes([symbol], market)
        return quotes[0] if quotes else None


def get_portfolio_market_service() -> PortfolioMarketService:
    return PortfolioMarketService()
