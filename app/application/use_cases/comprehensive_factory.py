from __future__ import annotations
"""Comprehensive UseCase Factory - All use cases."""


from .market_use_cases import (
    GetStockQuotesUseCase,
    GetStockQuotesByStockServiceUseCase,
    GetMarketPanoramaUseCase,
    GetMarketMovementsUseCase,
    GetMarketSentimentUseCase,
    GetStockDetailUseCase,
    GetStockHistoryUseCase,
)
from .watchlist_use_cases import (
    GetWatchlistUseCase,
    AddToWatchlistUseCase,
    RemoveFromWatchlistUseCase,
    GetWatchlistGroupsUseCase,
)
from .portfolio_use_cases import (
    GetPortfolioUseCase,
    GetPortfolioPositionsUseCase,
    UpdatePortfolioUseCase,
    GetPortfolioPerformanceUseCase,
)
from .news_use_cases import (
    GetMarketHeadlinesUseCase,
    GetStockNewsUseCase,
    GetStockNewsArchiveUseCase,
    GetIndustryNewsUseCase,
)


class UseCaseFactory:
    """Comprehensive factory for all UseCases."""

    def __init__(
        self,
        market_service=None,
        stock_service=None,
        watchlist_service=None,
        portfolio_service=None,
        news_provider=None,
        news_archive=None,
    ):
        self._market_service = market_service
        self._stock_service = stock_service
        self._watchlist_service = watchlist_service
        self._portfolio_service = portfolio_service
        self._news_provider = news_provider
        self._news_archive = news_archive

    # Market UseCases
    def get_stock_quotes(self) -> GetStockQuotesUseCase:
        return GetStockQuotesUseCase(self._market_service)

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

    # Watchlist UseCases
    def get_watchlist(self) -> GetWatchlistUseCase:
        return GetWatchlistUseCase(self._watchlist_service)

    def add_to_watchlist(self) -> AddToWatchlistUseCase:
        return AddToWatchlistUseCase(self._watchlist_service)

    def remove_from_watchlist(self) -> RemoveFromWatchlistUseCase:
        return RemoveFromWatchlistUseCase(self._watchlist_service)

    def get_watchlist_groups(self) -> GetWatchlistGroupsUseCase:
        return GetWatchlistGroupsUseCase(self._watchlist_service)

    # Portfolio UseCases
    def get_portfolio(self) -> GetPortfolioUseCase:
        return GetPortfolioUseCase(self._portfolio_service)

    def get_portfolio_positions(self) -> GetPortfolioPositionsUseCase:
        return GetPortfolioPositionsUseCase(self._portfolio_service)

    def update_portfolio(self) -> UpdatePortfolioUseCase:
        return UpdatePortfolioUseCase(self._portfolio_service)

    def get_portfolio_performance(self) -> GetPortfolioPerformanceUseCase:
        return GetPortfolioPerformanceUseCase(self._portfolio_service)

    # News UseCases
    def get_market_headlines(self) -> GetMarketHeadlinesUseCase:
        return GetMarketHeadlinesUseCase(self._news_provider)

    def get_stock_news(self) -> GetStockNewsUseCase:
        return GetStockNewsUseCase(self._stock_service, self._news_provider)

    def get_stock_news_archive(self) -> GetStockNewsArchiveUseCase:
        return GetStockNewsArchiveUseCase(self._news_archive)

    def get_industry_news(self) -> GetIndustryNewsUseCase:
        return GetIndustryNewsUseCase(self._news_provider)