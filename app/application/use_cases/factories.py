from __future__ import annotations
"""UseCase Factory - Dependency injection for UseCases."""


from .market_use_cases import (
    GetStockQuotesUseCase,
    GetStockQuotesByStockServiceUseCase,
    GetMarketPanoramaUseCase,
    GetMarketMovementsUseCase,
    GetMarketSentimentUseCase,
    GetStockDetailUseCase,
    GetStockHistoryUseCase,
)


class MarketUseCaseFactory:
    """Factory for creating market-related UseCases."""

    def __init__(self, market_service, stock_service):
        self._market_service = market_service
        self._stock_service = stock_service

    def get_stock_quotes(self) -> GetStockQuotesUseCase:
        return GetStockQuotesUseCase(self._market_service)

    def get_stock_quotes_via_stock_service(self) -> GetStockQuotesByStockServiceUseCase:
        return GetStockQuotesByStockServiceUseCase(self._stock_service)

    def get_market_panorama(self) -> GetMarketPanoramaUseCase:
        return GetMarketPanoramaUseCase(self._market_service)

    def get_market_movements(self) -> GetMarketMovementsUseCase:
        return GetMarketMovementsUseCase(self._market_service)

    def get_market_sentiment(self) -> GetMarketSentimentUseCase:
        return GetMarketSentimentUseCase(self._market_service)

    def get_stock_detail(self) -> GetStockDetailUseCase:
        return GetStockDetailUseCase(self._stock_service)

    def get_stock_history(self) -> GetStockHistoryUseCase:
        return GetStockHistoryUseCase(self._stock_service)
