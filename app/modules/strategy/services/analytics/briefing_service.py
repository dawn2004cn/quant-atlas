from __future__ import annotations

"""Personalized Morning/Evening Briefing Service."""


from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BriefingSection:
    """A section of the briefing."""
    title: str
    content: str
    icon: str = ""
    priority: int = 0


@dataclass
class MarketSummary:
    """Market summary for briefing."""
    index: float = 0.0
    change_pct: float = 0.0
    sentiment: str = ""
    hot_sectors: list[str] = field(default_factory=list)
    risk_level: str = "moderate"


@dataclass
class PositionAlert:
    """Position alert for user's holdings."""
    symbol: str
    name: str
    alert_type: str  # "warning", "opportunity", "info"
    message: str
    action_suggested: str = ""


@dataclass
class WatchlistPulse:
    """Pulse update for watched stocks."""
    symbol: str
    name: str
    change_pct: float
    volume_ratio: float
    news_count: int = 0


@dataclass
class Briefing:
    """Complete briefing data structure."""
    user_id: str
    briefing_type: str  # "morning", "evening"
    generated_at: datetime

    market_summary: MarketSummary | None = None
    positions: list[PositionAlert] = field(default_factory=list)
    watchlist: list[WatchlistPulse] = field(default_factory=list)
    sections: list[BriefingSection] = field(default_factory=list)

    total_duration_seconds: int = 30  # Estimated reading time


class BriefingGenerator:
    """Generate personalized briefing for users."""

    def __init__(self):
        self._services = {}

    def set_service(self, name: str, service: object) -> None:
        """Set a service for generating briefing parts."""
        self._services[name] = service

    def generate_morning_briefing(
        self,
        user_id: str,
        positions: list[dict],
        watchlist: list[dict],
        market_data: dict | None = None
    ) -> Briefing:
        """Generate morning briefing (8:50 AM)."""
        briefing = Briefing(
            user_id=user_id,
            briefing_type="morning",
            generated_at=datetime.now()
        )

        # 1. Market Summary
        if market_data:
            briefing.market_summary = self._generate_market_summary(market_data)
            briefing.sections.append(BriefingSection(
                title="市场体温?",
                content=self._format_market_summary(briefing.market_summary),
                icon="🌡?",
                priority=1
            ))

        # 2. Position Alerts
        briefing.positions = self._analyze_positions(positions)
        if briefing.positions:
            briefing.sections.append(BriefingSection(
                title="持仓预警",
                content=self._format_position_alerts(briefing.positions),
                icon="⚠️",
                priority=1
            ))

        # 3. Watchlist Pulse
        briefing.watchlist = self._analyze_watchlist(watchlist)
        if briefing.watchlist:
            briefing.sections.append(BriefingSection(
                title="关注动?",
                content=self._format_watchlist(briefing.watchlist),
                icon="👁?",
                priority=2
            ))

        # 4. Today's Strategy Suggestion
        briefing.sections.append(BriefingSection(
            title="今日策略",
            content=self._generate_strategy_suggestion(briefing.market_summary),
            icon="📈",
            priority=3
        ))

        # Estimate reading time
        briefing.total_duration_seconds = len(briefing.sections) * 10

        return briefing

    def generate_evening_briefing(
        self,
        user_id: str,
        positions: list[dict],
        watchlist: list[dict],
        daily_pnl: float = 0.0
    ) -> Briefing:
        """Generate evening briefing (3:30 PM)."""
        briefing = Briefing(
            user_id=user_id,
            briefing_type="evening",
            generated_at=datetime.now()
        )

        # 1. Daily P&L Summary
        pnl_section = BriefingSection(
            title="今日收益",
            content=self._format_daily_pnl(daily_pnl),
            icon="💰",
            priority=1
        )
        briefing.sections.append(pnl_section)

        # 2. Position Performance
        briefing.positions = self._analyze_positions(positions)
        if briefing.positions:
            briefing.sections.append(BriefingSection(
                title="持仓表现",
                content=self._format_position_alerts(briefing.positions),
                icon="📊",
                priority=2
            ))

        # 3. Tomorrow's Watch List
        briefing.sections.append(BriefingSection(
            title="明日关注",
            content=self._generate_tomorrow_watchlist(briefing.watchlist),
            icon="🔭",
            priority=3
        ))

        briefing.total_duration_seconds = len(briefing.sections) * 10

        return briefing

    def _generate_market_summary(self, data: dict) -> MarketSummary:
        """Generate market summary."""
        return MarketSummary(
            index=data.get("index", 0),
            change_pct=data.get("change_pct", 0),
            sentiment=data.get("sentiment", "neutral"),
            hot_sectors=data.get("hot_sectors", []),
            risk_level=data.get("risk_level", "moderate")
        )

    def _format_market_summary(self, summary: MarketSummary) -> str:
        """Format market summary as readable text."""
        trend = "上涨" if summary.change_pct > 0 else "下跌"
        sentiment_text = {
            "bullish": "偏暖",
            "neutral": "中?",
            "bearish": "偏冷"
        }.get(summary.sentiment, "中?")

        lines = [
            f"今日市场{trend} {abs(summary.change_pct):.2f}%，市场情绪{sentiment_text}?",
        ]

        if summary.hot_sectors:
            lines.append(f"热门板块：{', '.join(summary.hot_sectors[:3])}")

        if summary.risk_level == "high":
            lines.append("⚠️ 当前市场风险较高，建议谨慎操作?")
        elif summary.risk_level == "low":
            lines.append("??市场风险较低，可以适度乐观?")

        return " ".join(lines)

    def _analyze_positions(self, positions: list[dict]) -> list[PositionAlert]:
        """Analyze positions and generate alerts."""
        alerts = []

        for pos in positions:
            symbol = pos.get("symbol", "")
            name = pos.get("name", "")
            pnl_pct = pos.get("pnl_pct", 0)
            risk = pos.get("risk_level", "")

            if pnl_pct < -5:
                alerts.append(PositionAlert(
                    symbol=symbol,
                    name=name,
                    alert_type="warning",
                    message=f"亏损 {abs(pnl_pct):.1f}%，注意风?",
                    action_suggested="考虑止损"
                ))
            elif pnl_pct > 5:
                alerts.append(PositionAlert(
                    symbol=symbol,
                    name=name,
                    alert_type="opportunity",
                    message=f"盈利 {pnl_pct:.1f}%",
                    action_suggested="关注是否止盈"
                ))

            if risk == "high":
                alerts.append(PositionAlert(
                    symbol=symbol,
                    name=name,
                    alert_type="warning",
                    message="波动较大",
                    action_suggested="密切关注"
                ))

        return alerts[:5]  # Limit to 5 alerts

    def _format_position_alerts(self, alerts: list[PositionAlert]) -> str:
        """Format position alerts."""
        if not alerts:
            return "今日持仓无异常提醒?"

        lines = []
        for a in alerts:
            icon = {"warning": "⚠️", "opportunity": "🎯", "info": "ℹ️"}.get(a.alert_type, "")
            lines.append(f"{icon} {a.name}: {a.message}")

        return " ".join(lines)

    def _analyze_watchlist(self, watchlist: list[dict]) -> list[WatchlistPulse]:
        """Analyze watchlist for significant changes."""
        pulses = []

        for stock in watchlist:
            change_pct = stock.get("change_pct", 0)
            volume_ratio = stock.get("volume_ratio", 1)

            if abs(change_pct) > 3 or volume_ratio > 2:
                pulses.append(WatchlistPulse(
                    symbol=stock.get("symbol", ""),
                    name=stock.get("name", ""),
                    change_pct=change_pct,
                    volume_ratio=volume_ratio,
                    news_count=stock.get("news_count", 0)
                ))

        return pulses[:5]

    def _format_watchlist(self, pulses: list[WatchlistPulse]) -> str:
        """Format watchlist updates."""
        if not pulses:
            return "关注的股票今日无明显异动?"

        lines = []
        for p in pulses:
            direction = "?? if p.change_pct > 0 else "
            lines.append(f"{p.name} {direction}{abs(p.change_pct):.1f}%")

        return " ".join(lines)

    def _generate_strategy_suggestion(self, summary: MarketSummary | None) -> str:
        """Generate daily strategy suggestion."""
        if not summary:
            return "建议保持谨慎，关注市场动态?"

        if summary.risk_level == "high":
            return "建议降低仓位，等待市场企稳?"
        elif summary.sentiment == "bullish":
            return "市场情绪偏暖，可适度参与但需精选个股?"
        else:
            return "建议观望为主，等待明确信号?"

    def _format_daily_pnl(self, pnl: float) -> str:
        """Format daily P&L."""
        if pnl > 0:
            return f"今日盈利 {pnl:.2f} 元，继续保持?"
        elif pnl < 0:
            return f"今日亏损 {abs(pnl):.2f} 元，注意风险控制?"
        else:
            return "今日持平，静待机会?"

    def _generate_tomorrow_watchlist(self, watchlist: list[WatchlistPulse]) -> str:
        """Generate tomorrow's watchlist suggestion."""
        if not watchlist:
            return "建议明天继续关注市场热门板块?"

        symbols = [w.symbol for w in watchlist[:3]]
        return f"明日关注：{', '.join(symbols)}"


# Celery task integration
def schedule_morning_briefing(user_id: str) -> Briefing:
    """Schedule morning briefing for a user."""

    generator = BriefingGenerator()
    # In production, fetch actual data via services
    # For now, generate with mock data
    return generator.generate_morning_briefing(
        user_id=user_id,
        positions=[],
        watchlist=[],
        market_data={"index": 3200, "change_pct": 0.5, "sentiment": "neutral", "risk_level": "low"}
    )


__all__ = [
    "BriefingSection",
    "MarketSummary",
    "PositionAlert",
    "WatchlistPulse",
    "Briefing",
    "BriefingGenerator",
    "schedule_morning_briefing"
]
