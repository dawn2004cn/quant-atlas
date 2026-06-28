from __future__ import annotations

"""Technical analysis domain models."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.models.risk_models import PriceLevel


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


@dataclass
class TechnicalIndicators:
    code: str
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    rsi: float = 50.0
    rsi_14: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    kdj_k: float = 50.0
    kdj_d: float = 50.0
    kdj_j: float = 50.0
    boll_upper: float = 0.0
    boll_middle: float = 0.0
    boll_lower: float = 0.0
    atr: float = 0.0


@dataclass
class AnalysisResult:
    code: str
    name: str = ""
    overall_score: float = 0.0
    recommendation: str = "hold"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class Analyzer:
    """Pure technical helpers."""

    @staticmethod
    def calculate_trend(indicators: TechnicalIndicators) -> TrendDirection:
        if indicators.ma5 > indicators.ma20 * 1.002 and indicators.rsi < 75:
            return TrendDirection.UP
        if indicators.ma5 < indicators.ma20 * 0.998:
            return TrendDirection.DOWN
        return TrendDirection.SIDEWAYS

    @staticmethod
    def calculate_momentum(indicators: TechnicalIndicators) -> float:
        base = (indicators.ma5 - indicators.ma20) / indicators.ma20 * 100.0 if indicators.ma20 else 0.0
        return base + indicators.macd * 0.1 + (indicators.rsi - 50) * 0.05

    @staticmethod
    def find_support_levels(prices: list[float]) -> list[PriceLevel]:
        if not prices:
            return []
        lo = min(prices)
        return [PriceLevel(lo, "min"), PriceLevel(lo + (max(prices) - lo) * 0.25, "fib25")]

    @staticmethod
    def find_resistance_levels(prices: list[float]) -> list[PriceLevel]:
        if not prices:
            return []
        hi = max(prices)
        return [PriceLevel(hi, "max"), PriceLevel(hi - (hi - min(prices)) * 0.25, "fib25")]

    @staticmethod
    def calculate_fibonacci_levels(high: float, low: float) -> dict[str, float]:
        span = high - low
        return {
            "0%": high,
            "23.6%": high - 0.236 * span,
            "38.2%": high - 0.382 * span,
            "50%": high - 0.5 * span,
            "61.8%": low + 0.618 * span,
        }


class AnalysisService:
    """High-level analysis orchestration."""

    @staticmethod
    def analyze_stock(
        code: str,
        name: str,
        price: float,
        indicators: TechnicalIndicators,
        history_prices: list[float] | None = None,
    ) -> AnalysisResult:
        trend = Analyzer.calculate_trend(indicators)
        momentum = Analyzer.calculate_momentum(indicators)
        score = 50.0
        if trend == TrendDirection.UP:
            score += 15.0
        elif trend == TrendDirection.DOWN:
            score -= 15.0
        score += max(-20.0, min(20.0, momentum))
        if indicators.rsi > 70:
            score -= 10.0
        if indicators.rsi < 30:
            score += 5.0
        score = max(1.0, min(100.0, score))

        if score >= 75:
            rec = "strong_buy"
        elif score >= 60:
            rec = "buy"
        elif score >= 40:
            rec = "hold"
        elif score >= 25:
            rec = "sell"
        else:
            rec = "strong_sell"

        details: dict[str, Any] = {"trend": trend.value, "momentum": momentum}
        if history_prices:
            details["history_len"] = len(history_prices)

        return AnalysisResult(
            code=code,
            name=name,
            overall_score=score,
            recommendation=rec,
            details=details,
        )
