from __future__ import annotations
"""Market regime, sentiment, and calendar helpers."""


import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    RECOVERY = "recovery"


@dataclass
class MarketSentiment:
    market: str = "CN"
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    total_stocks: int = 0
    up_ratio: float = 0.0
    down_ratio: float = 0.0
    sentiment_score: float = 0.0
    timestamp: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        self.total_stocks = self.up_count + self.down_count + self.flat_count
        if self.total_stocks:
            self.up_ratio = self.up_count / self.total_stocks
            self.down_ratio = self.down_count / self.total_stocks
            self.sentiment_score = (self.up_count - self.down_count) / self.total_stocks * 100.0


class MarketAnalyzer:
    """Cross-sectional and time-series market stats."""

    @staticmethod
    def calculate_market_sentiment(stocks: list[dict]) -> MarketSentiment:
        up = down = flat = 0
        for s in stocks:
            ch = float(s.get("change_pct", 0.0))
            if ch > 0:
                up += 1
            elif ch < 0:
                down += 1
            else:
                flat += 1
        return MarketSentiment(market="CN", up_count=up, down_count=down, flat_count=flat)

    @staticmethod
    def detect_regime(prices: list[float], window: int = 20) -> MarketRegime:
        if len(prices) < max(5, window // 2):
            return MarketRegime.SIDEWAYS
        recent = prices[-window:] if len(prices) >= window else prices
        first = statistics.mean(recent[: len(recent) // 2])
        second = statistics.mean(recent[len(recent) // 2 :])
        slope = (recent[-1] - recent[0]) / max(len(recent), 1)
        vol = statistics.pstdev(recent) if len(recent) > 1 else 0.0

        if slope > vol * 0.3 and second > first:
            return MarketRegime.BULL
        if slope < -vol * 0.3 and second < first:
            return MarketRegime.BEAR
        if abs(slope) < vol * 0.15:
            return MarketRegime.SIDEWAYS
        return MarketRegime.RECOVERY

    @staticmethod
    def find_market_turning_points(prices: list[float]) -> list[float]:
        if len(prices) < 3:
            return []
        points: list[float] = []
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                points.append(prices[i])
            elif prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                points.append(prices[i])
        return points


class CalendarService:
    """Minimal weekday-based calendar (holidays not modeled)."""

    @staticmethod
    def is_trading_day(date: datetime, market: str = "CN") -> bool:
        _ = market
        return date.weekday() < 5

    @staticmethod
    def get_next_trading_day(date: datetime, market: str = "CN") -> datetime:
        _ = market
        d = date
        for _ in range(10):
            d = d + timedelta(days=1)
            if d.weekday() < 5:
                return d
        return d + timedelta(days=1)
