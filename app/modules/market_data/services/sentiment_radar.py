from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Market Sentiment Radar & Pulse Alert System."""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MarketDiary:
    """Daily market diary entry."""
    date: datetime
    overall_sentiment: str  # "bullish", "neutral", "bearish"
    summary: str  # Human-readable summary
    key_events: List[str] = field(default_factory=list)
    sector_sentiment: Dict[str, str] = field(default_factory=dict)


@dataclass
class SentimentPulse:
    """Pulse alert for hot stocks/sectors."""
    symbol: str
    name: str
    pulse_type: str  # "stock", "sector", "topic"
    sentiment_score: float  # -1 to 1
    velocity: str  # "rising", "stable", "falling"
    trigger_reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RadarConfig:
    """Configuration for sentiment radar."""
    pulse_threshold: float = 0.7  # Score threshold for pulse
    velocity_threshold: float = 0.3  # Change rate for velocity detection
    cooldown_minutes: int = 60  # Minimum time between pulses


class SentimentRadar:
    """Market sentiment radar with real-time monitoring."""

    def __init__(self, config: Optional[RadarConfig] = None):
        self.config = config or RadarConfig()
        self._last_pulses: Dict[str, datetime] = {}
        self._sentiment_history: List[MarketDiary] = []

    def generate_market_diary(self, market_data: Dict) -> MarketDiary:
        """Generate daily market diary."""
        today = datetime.now()

        # Analyze market data
        index_change = market_data.get("index_change", 0)
        volume_change = market_data.get("volume_change", 0)
        hot_sectors = market_data.get("hot_sectors", [])

        # Determine sentiment
        if index_change > 1 and volume_change > 20:
            sentiment = "bullish"
        elif index_change < -1 or volume_change < -20:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        # Generate summary
        summary = self._generate_diary_summary(sentiment, index_change, hot_sectors)

        return MarketDiary(
            date=today,
            overall_sentiment=sentiment,
            summary=summary,
            key_events=market_data.get("events", []),
            sector_sentiment=market_data.get("sector_sentiment", {})
        )

    def _generate_diary_summary(
        self,
        sentiment: str,
        index_change: float,
        hot_sectors: List[str]
    ) -> str:
        """Generate human-readable diary summary."""
        summaries = {
            "bullish": [
                f"今日市场偏暖，主要指数上涨 {index_change:.2f}%。",
                "市场情绪乐观，交投活跃。",
            ],
            "neutral": [
                f"今日市场横盘整理，指数变动 {index_change:+.2f}%。",
                "市场观望情绪浓厚。",
            ],
            "bearish": [
                f"今日市场偏冷，主要指数下跌 {abs(index_change):.2f}%。",
                "市场情绪回落，建议保持谨慎。",
            ]
        }

        base = summaries.get(sentiment, summaries["neutral"])

        if hot_sectors:
            base.append(f"热门板块：{', '.join(hot_sectors[:3])}。")

        return " ".join(base)

    def check_for_pulses(
        self,
        stocks: List[Dict],
        news_data: List[Dict]
    ) -> List[SentimentPulse]:
        """Check for sentiment pulses."""
        pulses = []
        now = datetime.now()

        # Check stock pulses
        for stock in stocks:
            # Skip if in cooldown
            symbol = stock.get("symbol", "")
            if symbol in self._last_pulses:
                last_time = self._last_pulses[symbol]
                if (now - last_time).total_seconds() < self.config.cooldown_minutes * 60:
                    continue

            # Calculate sentiment score
            score = self._calculate_sentiment_score(stock, news_data)

            # Check velocity
            velocity = self._detect_velocity(stock)

            if abs(score) >= self.config.pulse_threshold:
                pulse = SentimentPulse(
                    symbol=symbol,
                    name=stock.get("name", symbol),
                    pulse_type="stock",
                    sentiment_score=score,
                    velocity=velocity,
                    trigger_reason=self._get_trigger_reason(score, stock)
                )
                pulses.append(pulse)
                self._last_pulses[symbol] = now

        # Check sector pulses
        sector_scores = self._aggregate_sector_sentiment(stocks)
        for sector, score in sector_scores.items():
            if abs(score) >= self.config.pulse_threshold:
                pulses.append(SentimentPulse(
                    symbol=sector,
                    name=sector,
                    pulse_type="sector",
                    sentiment_score=score,
                    velocity="rising" if score > 0 else "falling",
                    trigger_reason=f"板块情绪突变"
                ))

        return sorted(pulses, key=lambda x: abs(x.sentiment_score), reverse=True)[:10]

    def _calculate_sentiment_score(self, stock: Dict, news_data: List[Dict]) -> float:
        """Calculate sentiment score for a stock."""
        score = 0.0

        # Price momentum
        change_pct = stock.get("change_pct", 0)
        if change_pct > 5:
            score += 0.3
        elif change_pct > 2:
            score += 0.1
        elif change_pct < -5:
            score -= 0.3
        elif change_pct < -2:
            score -= 0.1

        # Volume
        volume_ratio = stock.get("volume_ratio", 1)
        if volume_ratio > 2:
            score += 0.2 * (1 if change_pct > 0 else -1)
        elif volume_ratio > 1.5:
            score += 0.1 * (1 if change_pct > 0 else -1)

        # News sentiment (simplified)
        stock_news = [n for n in news_data if n.get("symbol") == stock.get("symbol")]
        if stock_news:
            news_sentiment = sum(n.get("sentiment", 0) for n in stock_news) / len(stock_news)
            score += news_sentiment * 0.3

        return max(-1, min(1, score))

    def _detect_velocity(self, stock: Dict) -> str:
        """Detect sentiment velocity."""
        # In real implementation, would compare to historical data
        volume_ratio = stock.get("volume_ratio", 1)
        change_pct = stock.get("change_pct", 0)

        if volume_ratio > 2 and abs(change_pct) > 3:
            return "rising" if change_pct > 0 else "falling"
        return "stable"

    def _get_trigger_reason(self, score: float, stock: Dict) -> str:
        """Get human-readable trigger reason."""
        if score > 0.7:
            return f"股价大涨 {stock.get('change_pct', 0):.1f}%，成交量激增"
        elif score > 0.3:
            return f"股价上涨 {stock.get('change_pct', 0):.1f}%，市场关注度上升"
        elif score < -0.7:
            return f"股价大跌 {abs(stock.get('change_pct', 0)):.1f}%，可能存在风险"
        elif score < -0.3:
            return f"股价下跌 {abs(stock.get('change_pct', 0)):.1f}%"
        return "市场情绪异常"

    def _aggregate_sector_sentiment(self, stocks: List[Dict]) -> GenericResponseDTO:
        """Aggregate sentiment by sector."""
        sector_scores: Dict[str, List[float]] = {}

        for stock in stocks:
            sector = stock.get("sector", "未知")
            score = self._calculate_sentiment_score(stock, [])

            if sector not in sector_scores:
                sector_scores[sector] = []
            sector_scores[sector].append(score)

        return {
            sector: sum(scores) / len(scores)
            for sector, scores in sector_scores.items()
            if scores
        }

    def get_recent_pulses(self, hours: int = 24) -> List[SentimentPulse]:
        """Get recent pulses within specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            pulse for pulse in self._get_all_pulses()
            if pulse.timestamp > cutoff
        ]

    def _get_all_pulses(self) -> List[SentimentPulse]:
        """Get all tracked pulses."""
        # In production, would fetch from database/cache
        return []


def generate_market_diary_text(diary: MarketDiary) -> str:
    """Generate market diary in text format for display."""
    date_str = diary.date.strftime("%Y年%m月%d日")

    lines = [
        f"📅 {date_str} 市场日记",
        "",
        f"🌡️ 市场体感：{'🔥 热' if diary.overall_sentiment == 'bullish' else ('❄️ 冷' if diary.overall_sentiment == 'bearish' else '➡️ 中性')}",
        "",
        diary.summary,
    ]

    if diary.key_events:
        lines.append("")
        lines.append("📌 关键事件：")
        for event in diary.key_events[:3]:
            lines.append(f"  • {event}")

    return "\n".join(lines)


__all__ = [
    "MarketDiary",
    "SentimentPulse",
    "RadarConfig",
    "SentimentRadar",
    "generate_market_diary_text"
]