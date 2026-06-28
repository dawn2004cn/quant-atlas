from __future__ import annotations

"""Market-related UseCases - abstracts business logic from API routes."""



from app.domain.enums import MarketCode

from ..use_cases import UseCase, UseCaseResult


class GetStockQuotesUseCase(UseCase):
    """UseCase: Get multiple stock quotes."""

    def __init__(self, market_service):
        self._market_service = market_service

    def execute(
        self,
        symbols: list[str] | None = None,
        market: str = "CN",
        limit: int = 12000,
    ) -> UseCaseResult:
        try:
            market_code = MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            quotes = self._market_service.list_quotes(market_code, symbols)

            if limit and limit > 0 and len(quotes) > limit:
                quotes = quotes[:limit]

            return UseCaseResult.ok({"stocks": quotes, "count": len(quotes)})
        except Exception as e:
            return UseCaseResult.fail(f"获取行情失败: {e}")


class GetStockQuotesByStockServiceUseCase(UseCase):
    """UseCase: Get multiple stock quotes via StockService."""

    def __init__(self, stock_service):
        self._stock_service = stock_service

    def execute(
        self,
        symbols: list[str] | None = None,
        market: str = "CN",
        limit: int = 12000,
    ) -> UseCaseResult:
        try:
            MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            quotes = self._stock_service.list_quotes(market, symbols)

            if limit and limit > 0 and len(quotes) > limit:
                quotes = quotes[:limit]

            return UseCaseResult.ok({"stocks": quotes, "count": len(quotes)})
        except Exception as e:
            return UseCaseResult.fail(f"获取行情失败: {e}")


class GetMarketPanoramaUseCase(UseCase):
    """UseCase: Get market panorama with rankings."""

    def __init__(self, market_service):
        self._market_service = market_service

    def execute(self, market: str = "CN") -> UseCaseResult:
        try:
            market_code = MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            panorama = self._market_service.get_panorama(market_code)
            return UseCaseResult.ok(panorama)
        except Exception as e:
            return UseCaseResult.fail(f"获取市场全景失败: {e}")


class GetMarketMovementsUseCase(UseCase):
    """UseCase: Get market movements (up/down/neutral counts)."""

    def __init__(self, market_service):
        self._market_service = market_service

    def execute(self, market: str = "CN", top_n: int = 12) -> UseCaseResult:
        try:
            market_code = MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            movements = self._market_service.get_movements(market_code, top_n=top_n)
            return UseCaseResult.ok({"movements": movements})
        except Exception as e:
            return UseCaseResult.fail(f"获取市场涨跌失败: {e}")


class GetMarketSentimentUseCase(UseCase):
    """UseCase: Get market sentiment."""

    def __init__(self, market_service):
        self._market_service = market_service

    def execute(self, market: str = "CN") -> UseCaseResult:
        try:
            market_code = MarketCode.CN if market.upper() == "CN" else MarketCode.HK
            sentiment = self._market_service.get_sentiment(market_code)
            return UseCaseResult.ok(sentiment)
        except Exception as e:
            return UseCaseResult.fail(f"获取市场情绪失败: {e}")


class GetStockDetailUseCase(UseCase):
    """UseCase: Get single stock detail."""

    def __init__(self, stock_service):
        self._stock_service = stock_service

    def execute(self, code: str, market: str = "A") -> UseCaseResult:
        try:
            detail = self._stock_service.get_stock_detail(code, market)
            return UseCaseResult.ok(detail)
        except Exception as e:
            return UseCaseResult.fail(f"获取股票详情失败: {e}")


class GetStockHistoryUseCase(UseCase):
    """UseCase: Get stock historical data."""

    def __init__(self, stock_service):
        self._stock_service = stock_service

    def execute(
        self,
        code: str,
        market: str = "CN",
        start: str | None = None,
        end: str | None = None,
        limit: int = 1000,
    ) -> UseCaseResult:
        try:
            history = self._stock_service.get_history(
                code, market=market, start_date=start, end_date=end, limit=limit
            )
            return UseCaseResult.ok({"history": history})
        except Exception as e:
            return UseCaseResult.fail(f"获取历史数据失败: {e}")
