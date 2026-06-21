"""Autonomous Agent — Phase 15. Regime-aware proactive Jarvis with market triggers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.event_bus import get_event_bus
from app.core.logger import get_logger
from app.domain.services.market_regime_service import MarketRegimeService

logger = get_logger(__name__)


@dataclass
class ProactiveAlert:
    alert_id: str
    alert_type: str  # "regime_switch", "strategy_recommendation", "risk_warning"
    title: str
    message: str
    confidence: float = 0.0
    actionable: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutonomousAgentService:
    """Regime-aware proactive Jarvis — market changes → AI alerts → user confirms."""

    def __init__(self):
        self._regime = MarketRegimeService()
        self._bus = get_event_bus()

    def assess_market_and_alert(self, symbol: str = "000001.SH", market: str = "CN") -> ProactiveAlert | None:
        """Check current market regime and proactively suggest strategy switches."""
        try:
            analysis = self._regime.analyze_regime(symbol, market)
        except Exception:
            return None

        if not analysis:
            return None

        regime = analysis.get("regime", analysis.get("market_regime", "unknown"))
        score = analysis.get("score", analysis.get("temperature", 50))
        signal = analysis.get("signal", analysis.get("traffic_light", "yellow"))

        # ── Regime switch detection ──────────────────────────────────
        if signal == "red" or score < 30:
            return ProactiveAlert(
                alert_id=f"regime_{datetime.now(timezone.utc).timestamp():.0f}",
                alert_type="regime_switch",
                title="市场环境转换预警",
                message=f"检测到市场进入{regime}状态（温度{score}），建议暂停趋势策略，切换至防守或现金策略",
                confidence=0.85,
            )
        elif signal == "green" and score > 70:
            return ProactiveAlert(
                alert_id=f"regime_{datetime.now(timezone.utc).timestamp():.0f}",
                alert_type="strategy_recommendation",
                title="做多窗口开启",
                message=f"市场温度{score}分，处于{regime}，建议启用激进趋势策略",
                confidence=0.78,
            )
        elif signal == "yellow":
            return ProactiveAlert(
                alert_id=f"regime_{datetime.now(timezone.utc).timestamp():.0f}",
                alert_type="risk_warning",
                title="震荡市注意仓位",
                message=f"市场处于{regime}震荡区间（温度{score}），建议降低仓位，关注结构性机会",
                confidence=0.65,
            )

        return None
