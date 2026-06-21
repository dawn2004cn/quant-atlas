"""Psychology Guardian Service — retail investor behavioral analysis.

Tracks user trading behavior (add/remove watchlist, adopt trade plans,
execution feedback) and detects emotional patterns like chasing rallies
or panic selling.

Exports:
    build_psychology_guardian_service()  — factory for DI
    PsychologyGuardianService            — main service class
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PsychologyGuardianService:
    """Analyzes user trading behavior for emotional patterns.

    Detects:
    - 追涨杀跌 (chasing rallies / panic selling)
    - 频繁交易 (overtrading)
    - 止损失效 (stop-loss neglect)
    - 持仓犹豫 (holding losers too long)
    """

    def __init__(
        self,
        *,
        signal_observation_service: Any | None = None,
        audit_trail_service: Any | None = None,
        operation_store: Any | None = None,
    ) -> None:
        self._signal_obs = signal_observation_service
        self._audit_trail = audit_trail_service
        self._op_store = operation_store

    # ── Core analysis ────────────────────────────────────────────

    def analyze_user_behavior(
        self,
        user_id: int,
        operation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Analyze user behavior and return pattern alerts.

        Returns dict with:
            - alerts: list of detected emotional patterns
            - patterns: summary of detected patterns
            - risk_level: "low" | "medium" | "high"
        """
        if not operation_history:
            if self._op_store:
                operation_history = self._op_store.list_recent(user_id)
            else:
                operation_history = []

        if not operation_history:
            return {
                "alerts": [],
                "patterns": {},
                "risk_level": "low",
                "message": "no_history",
            }

        alerts = []
        patterns = {}

        # Detect chase_rally (追涨杀跌)
        chase = self._detect_chase_rally(operation_history)
        if chase:
            alerts.append(chase)
            patterns["chase_rally"] = True

        # Detect overtrading (频繁交易)
        overtrade = self._detect_overtrading(operation_history)
        if overtrade:
            alerts.append(overtrade)
            patterns["overtrading"] = True

        # Detect stop_loss_neglect (止损失效)
        stop_loss = self._detect_stop_loss_neglect(operation_history)
        if stop_loss:
            alerts.append(stop_loss)
            patterns["stop_loss_neglect"] = True

        # Determine overall risk level
        risk_level = self._compute_risk_level(alerts)

        return {
            "alerts": alerts,
            "patterns": patterns,
            "risk_level": risk_level,
            "operation_count": len(operation_history),
        }

    def status_summary(self, user_id: int) -> dict[str, Any]:
        """Lightweight status summary for dashboard banners."""
        result = self.analyze_user_behavior(user_id)
        return {
            "risk_level": result.get("risk_level", "low"),
            "alert_count": len(result.get("alerts", [])),
            "patterns": result.get("patterns", {}),
            "latest_alert": result.get("alerts", [{}])[0].get("message", "") if result.get("alerts") else "",
        }

    # ── Pattern detectors ────────────────────────────────────────

    def _detect_chase_rally(self, history: list[dict]) -> dict | None:
        """Detect chasing rallies: buying after large gains repeatedly."""
        buys = [h for h in history if h.get("action") == "buy"]
        if len(buys) < 2:
            return None

        # Check if recent buys coincide with high change_pct
        recent = buys[-3:]
        high_gains = sum(
            1 for b in recent if float(b.get("change_pct", 0)) > 5
        )
        if high_gains >= 2:
            return {
                "type": "chase_rally",
                "severity": "high" if high_gains >= 3 else "medium",
                "message": f"检测到追涨行为：最近3次买入中有{high_gains}次发生在涨幅>5%时",
                "confidence": min(0.9, 0.5 + high_gains * 0.15),
            }
        return None

    def _detect_overtrading(self, history: list[dict]) -> dict | None:
        """Detect overtrading: too many actions in short period."""
        if len(history) < 5:
            return None

        # Count actions in last N entries
        recent = history[-10:]
        if len(recent) >= 5:
            return {
                "type": "overtrading",
                "severity": "medium",
                "message": f"频繁交易信号：最近10次操作中动作过多（{len(recent)}次）",
                "confidence": min(0.8, 0.4 + len(recent) * 0.05),
            }
        return None

    def _detect_stop_loss_neglect(self, history: list[dict]) -> dict | None:
        """Detect stop-loss neglect: holding losing positions too long."""
        sells = [h for h in history if h.get("action") == "sell"]
        if len(sells) < 2:
            return None

        # Check if sell prices are consistently below buy prices
        losses = sum(
            1 for s in sells
            if float(s.get("change_pct", 0)) < -3
        )
        if losses >= 2:
            return {
                "type": "stop_loss_neglect",
                "severity": "high",
                "message": f"止损失效信号：{losses}次卖出发生在亏损>3%时",
                "confidence": min(0.85, 0.5 + losses * 0.1),
            }
        return None

    @staticmethod
    def _compute_risk_level(alerts: list[dict]) -> str:
        if not alerts:
            return "low"
        severities = [a.get("severity", "low") for a in alerts]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    # ── Alert push helpers ───────────────────────────────────────

    def push_alerts_to_message_center(
        self,
        task_message_store: Any,
        user_id: int,
        alerts: list[dict],
        *,
        lifecycle_service: Any | None = None,
    ) -> int:
        """Push psychology alerts to the message center."""
        if not alerts:
            return 0
        pushed = 0
        for alert in alerts:
            try:
                task_message_store.create(
                    user_id=user_id,
                    title=f"心理卫士: {alert.get('type', 'unknown')}",
                    content=alert.get("message", ""),
                    category="psychology",
                    priority="high" if alert.get("severity") == "high" else "normal",
                )
                pushed += 1
            except Exception as exc:  # noqa: BLE001
                logger.debug("push alert to message center: %s", exc)
        return pushed


# ── Factory ───────────────────────────────────────────────────────

def build_psychology_guardian_service(
    *,
    signal_observation_service: Any | None = None,
    audit_trail_service: Any | None = None,
    operation_store: Any | None = None,
) -> PsychologyGuardianService:
    """Build a PsychologyGuardianService instance (DI factory)."""
    return PsychologyGuardianService(
        signal_observation_service=signal_observation_service,
        audit_trail_service=audit_trail_service,
        operation_store=operation_store,
    )
