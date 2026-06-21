from __future__ import annotations
"""Analysis application service using domain models."""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.models.analysis_models import (
    TechnicalIndicators,
    AnalysisService,
    Analyzer,
    AnalysisResult,
)
from app.application.dto.complete_dto import (
    QuoteDTO,
)
from app.application.events import EventType, publish_event
from app.domain.dto.request_dtos import BatchAnalysisRequestDTO
from app.domain.dto.analysis_dto import TrendDTO, SupportResistanceDTO, FibonacciDTO

logger = get_logger(__name__)


class AnalysisApplicationService:
    """Application service for stock analysis using domain models."""

    def __init__(self, market_provider=None):
        self._market_provider = market_provider
        self._analysis_cache: dict[str, AnalysisResult] = {}
        logger.info("AnalysisApplicationService initialized")

    async def analyze_stock(
        self,
        code: str,
        name: str = "",
        history_prices: list[float] | None = None,
    ) -> AnalysisResult:
        """Analyze a stock using domain models."""
        quote = None

        if self._market_provider:
            try:
                quote = self._market_provider.get_realtime_quote(code)
            except Exception as e:
                logger.warning(f"Could not get quote for {code}: {e}")

        price = quote.get("price", 0) if quote else 0

        indicators = self._build_indicators(code, quote or {})

        result = AnalysisService.analyze_stock(
            code=code,
            name=name,
            price=price,
            indicators=indicators,
            history_prices=history_prices,
        )

        self._analysis_cache[code] = result

        await publish_event(
            EventType.ANALYSIS_COMPLETED,
            {
                "code": code,
                "score": result.overall_score,
                "recommendation": result.recommendation,
            },
            source="AnalysisApplicationService"
        )

        return result

    async def analyze_batch(
        self,
        request: BatchAnalysisRequestDTO,
    ) -> list[AnalysisResult]:
        """Analyze multiple stocks using DTOs."""
        results = []
        for stock in request.stocks:
            result = await self.analyze_stock(stock.code, stock.name, stock.history_prices)
            results.append(result)

        return results

    def calculate_trend_only(
        self,
        code: str,
        prices: list[float],
    ) -> TrendDTO:
        """Quick trend calculation."""
        if len(prices) < 5:
            return TrendDTO(trend="unknown", momentum=0, ma5=0.0, ma20=0.0)

        indicators = TechnicalIndicators(code=code)
        indicators.ma5 = sum(prices[-5:]) / 5
        indicators.ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else indicators.ma5

        trend = Analyzer.calculate_trend(indicators)
        momentum = Analyzer.calculate_momentum(indicators)

        return TrendDTO(
            trend=trend.value,
            momentum=momentum,
            ma5=indicators.ma5,
            ma20=indicators.ma20,
        )

    def find_support_resistance(
        self,
        prices: list[float],
    ) -> SupportResistanceDTO:
        """Find support and resistance levels."""
        supports = Analyzer.find_support_levels(prices)
        resistances = Analyzer.find_resistance_levels(prices)

        return SupportResistanceDTO(
            support=[s.price for s in supports[:5]],
            resistance=[r.price for r in resistances[:5]],
        )

    def calculate_fibonacci(
        self,
        high: float,
        low: float,
    ) -> FibonacciDTO:
        """Calculate Fibonacci retracement levels."""
        return FibonacciDTO(levels=Analyzer.calculate_fibonacci_levels(high, low))

    def clear_cache(self, code: str | None = None):
        """Clear analysis cache."""
        if code:
            self._analysis_cache.pop(code, None)
        else:
            self._analysis_cache.clear()

    def _build_indicators(self, code: str, quote: dict[str, Any]) -> TechnicalIndicators:
        """Build technical indicators from quote data."""
        indicators = TechnicalIndicators(code=code)

        indicators.ma5 = quote.get("ma5", 0)
        indicators.ma10 = quote.get("ma10", 0)
        indicators.ma20 = quote.get("ma20", 0)
        indicators.ma60 = quote.get("ma60", 0)

        indicators.rsi = quote.get("rsi", 50)
        indicators.rsi_14 = quote.get("rsi_14", 50)

        indicators.macd = quote.get("macd", 0)
        indicators.macd_signal = quote.get("macd_signal", 0)
        indicators.macd_hist = quote.get("macd_hist", 0)

        indicators.kdj_k = quote.get("kdj_k", 50)
        indicators.kdj_d = quote.get("kdj_d", 50)
        indicators.kdj_j = quote.get("kdj_j", 50)

        indicators.boll_upper = quote.get("boll_upper", 0)
        indicators.boll_middle = quote.get("boll_middle", 0)
        indicators.boll_lower = quote.get("boll_lower", 0)

        indicators.atr = quote.get("atr", 0)

        return indicators


__all__ = ["AnalysisApplicationService"]