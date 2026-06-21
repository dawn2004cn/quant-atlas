from __future__ import annotations
"""Strategy Copilot UseCase - 策略推荐引擎."""


from datetime import datetime, timedelta
from typing import Any

from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
from app.domain.enums import MarketCode
from app.domain.ports.market_ports import MarketDataProvider
from app.core.logger import get_logger

logger = get_logger(__name__)


class StrategyCopilotUseCase:
    """策略Copilot - 分析波动率和趋势，推荐匹配的策略."""

    def __init__(self, market_provider: MarketDataProvider | None = None):
        self._provider = market_provider

    def execute(self, symbol: str, market: MarketCode = MarketCode.CN) -> dict[str, Any]:
        provider = self._provider or get_market_data_provider()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        try:
            bars = provider.get_stock_history(symbol, market, start_date.isoformat(), end_date.isoformat())
            if not bars or len(bars) < 5:
                return {"error": "insufficient_data", "recommendations": []}

            prices = [b.get("close", 0) for b in bars if b.get("close")]
            if not prices:
                return {"error": "no_price_data", "recommendations": []}

            volatility = self._calculate_volatility(prices)
            trend = self._calculate_trend(prices)

            recommendations = self._generate_recommendations(volatility, trend)
            return {
                "symbol": symbol,
                "volatility": volatility,
                "trend": trend,
                "regime": self._classify_regime(volatility, trend),
                "recommendations": recommendations,
            }
        except Exception as e:
            logger.error("StrategyCopilot failed for %s: %s", symbol, e)
            return {"error": str(e), "recommendations": []}

    def _calculate_volatility(self, prices: list[float]) -> float:
        if len(prices) < 2:
            return 0.0
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return (variance ** 0.5) / mean * 100 if mean > 0 else 0.0

    def _calculate_trend(self, prices: list[float]) -> str:
        if len(prices) < 5:
            return "sideways"
        recent = prices[-5:]
        first, last = recent[0], recent[-1]
        pct_change = (last - first) / first * 100 if first > 0 else 0
        if pct_change > 3:
            return "uptrend"
        if pct_change < -3:
            return "downtrend"
        return "sideways"

    def _classify_regime(self, volatility: float, trend: str) -> str:
        if volatility > 5:
            regime = "high_volatility"
        elif volatility > 2:
            regime = "medium_volatility"
        else:
            regime = "low_volatility"

        if trend == "uptrend":
            regime += "_bullish"
        elif trend == "downtrend":
            regime += "_bearish"

        return regime

    def _generate_recommendations(self, volatility: float, trend: str) -> list[dict[str, Any]]:
        recommendations = []

        if volatility > 5:
            recommendations.extend([
                {"strategy": "grid_trading", "score": 0.9, "reason": "高波动适合网格交易"},
                {"strategy": "mean_reversion", "score": 0.7, "reason": "波动大适合均值回归"},
            ])
        elif volatility > 2:
            recommendations.extend([
                {"strategy": "dual_thrust", "score": 0.9, "reason": "中波动适合Dual Thrust"},
                {"strategy": "breakout", "score": 0.7, "reason": "趋势行情适合突破策略"},
            ])
        else:
            recommendations.extend([
                {"strategy": "trend_following", "score": 0.8, "reason": "低波动适合趋势跟踪"},
                {"strategy": "macd_divergence", "score": 0.6, "reason": "窄幅震荡适合MACD背离"},
            ])

        if trend == "uptrend":
            recommendations.append({"strategy": "momentum", "score": 0.85, "reason": "上升趋势适合动量策略"})
        elif trend == "downtrend":
            recommendations.append({"strategy": "short_reversal", "score": 0.7, "reason": "下降趋势适合空头反转"})

        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:5]


def get_strategy_copilot_use_case() -> StrategyCopilotUseCase:
    return StrategyCopilotUseCase()
