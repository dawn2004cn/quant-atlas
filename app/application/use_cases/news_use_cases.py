from __future__ import annotations
"""News-related UseCases."""


from ..use_cases import UseCase, UseCaseResult
from app.domain.enums import MarketCode


class GetMarketHeadlinesUseCase(UseCase):
    """UseCase: Get market headlines."""

    def __init__(self, news_provider):
        self._news_provider = news_provider

    def execute(self, market: str = "CN", limit: int = 40) -> UseCaseResult:
        try:
            market_code = MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            headlines = self._news_provider.get_market_headlines(market_code, limit=limit)
            return UseCaseResult.ok({"headlines": headlines, "count": len(headlines)})
        except Exception as e:
            return UseCaseResult.fail(f"获取快讯失败: {e}")


class GetStockNewsUseCase(UseCase):
    """UseCase: Get stock news."""

    def __init__(self, stock_service, news_provider):
        self._stock_service = stock_service
        self._news_provider = news_provider

    def execute(self, symbol: str, market: str = "CN") -> UseCaseResult:
        try:
            news = self._stock_service.get_news_snapshot(symbol, MarketCode.CN)
            return UseCaseResult.ok({"news": news})
        except Exception as e:
            return UseCaseResult.fail(f"获取新闻失败: {e}")


class GetStockNewsArchiveUseCase(UseCase):
    """UseCase: Get stock news archive."""

    def __init__(self, news_archive):
        self._news_archive = news_archive

    def execute(self, symbol: str, market: str = "CN", limit: int = 50) -> UseCaseResult:
        try:
            items = self._news_archive.list_for_symbol(market, symbol, limit=limit)
            meta = self._news_archive.get_meta(market, symbol)
            return UseCaseResult.ok({"news": items, "meta": meta})
        except Exception as e:
            return UseCaseResult.fail(f"获取历史新闻失败: {e}")


class GetIndustryNewsUseCase(UseCase):
    """UseCase: Get industry news."""

    def __init__(self, news_provider):
        self._news_provider = news_provider

    def execute(self, industry: str, market: str = "CN") -> UseCaseResult:
        try:
            news = self._news_provider.get_industry_news(industry, MarketCode.CN)
            return UseCaseResult.ok({"news": news})
        except Exception as e:
            return UseCaseResult.fail(f"获取行业新闻失败: {e}")