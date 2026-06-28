"""Jarvis Neural Connection — anomaly → strategy auto-recommendation.

Subscribes to the event bus for anomaly/deviation/regime events,
then routes each anomaly through archetype-aware recommendation logic
to suggest the right tool/strategy to the user.

Anomaly types handled:
- TruthDeviationEvent: multi-source data deviation (TDX vs Qlib)
- WatchlistAnomalyDetectedEvent: watchlist price/volume/risk anomalies
- MarketRegimeChangedEvent: bull/bear/sideways/crash shifts

Output: JarvisProactiveSuggestion with one_line_narrative, recommended_actions,
confidence score, and user context awareness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any

from app.core.event_bus import (
    MarketRegimeChangedEvent,
    TruthDeviationEvent,
    WatchlistAnomalyDetectedEvent,
    get_event_bus,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Recommendation data structures ────────────────────────────────

class AnomalyType(Enum):
    DATA_DEVIATION = auto()
    QUORUM_FAILURE = auto()
    MOMENTUM_SURGE = auto()
    VOLUME_SPIKE = auto()
    RISK_ALERT = auto()
    REGIME_SHIFT = auto()


class RecommendationType(Enum):
    ANALYZE = auto()           # Suggest deep analysis tool
    TRADE_PLAN = auto()        # Suggest pre-built trade plan
    FACTOR_ORTHOGONAL = auto() # Suggest factor analysis
    PATTER_MATCH = auto()      # Suggest historical pattern match
    RISK_CHECK = auto()        # Suggest risk evaluation
    WATCHLIST_ADD = auto()     # Suggest adding to watchlist
    BACKTEST = auto()          # Suggest backtesting


@dataclass
class RecommendedAction:
    """One actionable recommendation for the user."""
    rec_type: RecommendationType
    title: str
    description: str
    href: str  # URL path
    priority: int  # 1=highest


@dataclass
class JarvisProactiveSuggestion:
    """A proactive suggestion produced by the Jarvis Neural Connection."""
    symbol: str
    anomaly_type: str
    anomaly_score: float  # 0..1
    narrative: str  # human-readable explanation
    confidence: float  # 0..1
    recommended_actions: list[RecommendedAction] = field(default_factory=list)


# ── Neural Connection Router ─────────────────────────────────────

class JarvisNeuralConnection:
    """Routes anomalies through archetype-aware recommendation logic.

    The "neural" part: each anomaly type maps to a recommendation
    strategy, with archetype context adjusting the confidence and
    suggested actions.
    """

    def __init__(
        self,
        user_context=None,
        recommendation_service=None,
        canvas_predictive_service=None,
    ):
        self._user_context = user_context
        self._rec_service = recommendation_service
        self._canvas_svc = canvas_predictive_service
        self._suggestions: list[JarvisProactiveSuggestion] = []

    def on_truth_deviation(self, event: TruthDeviationEvent) -> JarvisProactiveSuggestion:
        """Handle multi-source data deviation anomaly."""
        symbol = (event.symbol or "").strip().upper()
        if not symbol:
            return None

        score = min(1.0, event.diff_pct / 5.0)  # normalize: 5% diff = max score
        source_a = event.source_a or "TDX"
        source_b = event.source_b or "Qlib"

        if score > 0.5:
            narrative = f"检测到 {symbol} 在 {source_a} vs {source_b} 间存在 {event.diff_pct:.2f}% 价差偏离，可能影响因子计算准确性"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="查看数据对账详情",
                    description=f"{source_a}={event.value_a:.3f} vs {source_b}={event.value_b:.3f}",
                    href=f"/data-truth?symbol={symbol}",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.FACTOR_ORTHOGONAL,
                    title="检查因子正交性",
                    description="偏差可能导致因子冗余",
                    href=f"/factor-catalog?symbol={symbol}",
                    priority=2,
                ),
            ]
        else:
            narrative = f"{symbol} 轻微微 dev ({event.diff_pct:.2f}%)，系统已自动处理"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.WATCHLIST_ADD,
                    title="在监控中保持关注",
                    description="轻微偏差，已加入自愈队列",
                    href=f"/self-stocks?symbol={symbol}",
                    priority=2,
                ),
            ]

        return self._build_suggestion(symbol, "data_deviation", score, narrative, actions)

    def on_watchlist_anomaly(self, event: WatchlistAnomalyDetectedEvent) -> JarvisProactiveSuggestion:
        """Handle watchlist anomaly (price, volume, risk)."""
        symbol = (event.symbol or "").strip().upper()
        if not symbol:
            return None

        anomaly_type = event.anomaly_type or "unknown"
        score = event.score / 100.0 if event.score else 0.5
        narrative = ""
        actions = []

        if anomaly_type == "momentum":
            narrative = f"监测到 {symbol} 出现强势异动 ({event.message})，主力资金净流入迹象"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.TRADE_PLAN,
                    title="一键生成交易计划",
                    description="基于当前异动特征自动构建",
                    href=f"/trade-plan/plan?symbol={symbol}",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="AI 深度分析",
                    description="量价关系 + 筹码分布解读",
                    href=f"/ai-analysis/{symbol}",
                    priority=2,
                ),
            ]
        elif anomaly_type == "volume":
            narrative = f"监测到 {symbol} 放量异动，成交量较均值放大"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.PATTER_MATCH,
                    title="历史回响匹配",
                    description="查看历史相似放量走势",
                    href=f"/phase18/resonance?symbol={symbol}",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="订单流分析",
                    description="资金流向拆解",
                    href=f"/ai-analysis/{symbol}?tool=order_flow",
                    priority=2,
                ),
            ]
        elif anomaly_type == "risk":
            narrative = f"预警 {symbol} 高风险特征：{event.message}"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.RISK_CHECK,
                    title="风险评估",
                    description="持仓压力测试与止损建议",
                    href=f"/portfolio/risk?symbol={symbol}",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="查看压力测试",
                    description="极端行情模拟",
                    href=f"/ai-analysis/{symbol}?tool=stress_test",
                    priority=2,
                ),
            ]
        else:
            narrative = f"{symbol} 异常信号: {event.message}"
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="查看详情",
                    description=event.message,
                    href=f"/ai-analysis/{symbol}",
                    priority=2,
                ),
            ]

        return self._build_suggestion(symbol, anomaly_type, score, narrative, actions)

    def on_regime_change(self, event: MarketRegimeChangedEvent) -> JarvisProactiveSuggestion:
        """Handle market regime shift (bull/bear/crash etc)."""
        new_regime = event.new_regime or "unknown"
        confidence = event.confidence or 0.5

        narrative = f"市场风格切换为 {self._regime_label(new_regime)} (置信度 {confidence:.0%})"
        actions = []

        if new_regime in ("bear", "crash"):
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.RISK_CHECK,
                    title="全局风控检查",
                    description="市场转空，建议降低仓位",
                    href="/portfolio/risk",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.BACKTEST,
                    title="回测防御策略",
                    description="熊市中表现最佳的策略组合",
                    href="/backtest?strategy=defensive",
                    priority=2,
                ),
            ]
        elif new_regime == "bull":
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.TRADE_PLAN,
                    title="寻找进攻机会",
                    description="牛市中的强势板块分析",
                    href="/ai-committee",
                    priority=1,
                ),
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="板块轮动雷达",
                    description="资金流向 hottest sectors",
                    href="/hot-sectors",
                    priority=2,
                ),
            ]
        else:
            actions = [
                RecommendedAction(
                    rec_type=RecommendationType.ANALYZE,
                    title="市场全景",
                    description=f"当前 {self._regime_label(new_regime)} 市场特征",
                    href="/market-panorama",
                    priority=2,
                ),
            ]

        return JarvisProactiveSuggestion(
            symbol="",  # Global event
            anomaly_type=f"regime:{new_regime}",
            anomaly_score=confidence,
            narrative=narrative,
            confidence=confidence,
            recommended_actions=actions,
        )

    def _build_suggestion(
        self,
        symbol: str,
        anomaly_type: str,
        score: float,
        narrative: str,
        actions: list[RecommendedAction],
    ) -> JarvisProactiveSuggestion:
        suggestion = JarvisProactiveSuggestion(
            symbol=symbol,
            anomaly_type=anomaly_type,
            anomaly_score=min(1.0, max(0.0, score)),
            narrative=narrative,
            confidence=min(0.95, 0.5 + score * 0.4),
            recommended_actions=actions,
        )
        self._suggestions.append(suggestion)
        logger.info("Jarvis suggestion: %s for %s (score=%.2f)", anomaly_type, symbol, score)
        return suggestion

    @staticmethod
    def _regime_label(regime: str) -> str:
        labels = {
            "bull": "牛市",
            "bear": "熊市",
            "sideways": "震荡",
            "crash": "暴跌",
            "recovery": "复苏",
        }
        return labels.get(regime, regime)

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent suggestions as serializable dicts."""
        recent = self._suggestions[-limit:]
        return [
            {
                "symbol": s.symbol,
                "anomaly_type": s.anomaly_type,
                "anomaly_score": s.anomaly_score,
                "narrative": s.narrative,
                "confidence": s.confidence,
                "actions": [
                    {
                        "title": a.title,
                        "description": a.description,
                        "href": a.href,
                        "priority": a.priority,
                    }
                    for a in s.recommended_actions
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for s in recent
        ]

    def clear(self) -> None:
        self._suggestions.clear()


# ── EventBus wiring helper ────────────────────────────────────────

def wire_jarvis_neural_connection(jarvis_conn: JarvisNeuralConnection | None = None) -> JarvisNeuralConnection:
    """Subscribe JarvisNeuralConnection to relevant event bus events.

    Returns the connection instance so callers can use it directly.
    """
    if jarvis_conn is None:
        jarvis_conn = JarvisNeuralConnection()

    bus = get_event_bus()

    # Subscribe to anomaly/deviation events
    bus.subscribe(TruthDeviationEvent, jarvis_conn.on_truth_deviation, priority=50)
    bus.subscribe(WatchlistAnomalyDetectedEvent, jarvis_conn.on_watchlist_anomaly, priority=50)
    bus.subscribe(MarketRegimeChangedEvent, jarvis_conn.on_regime_change, priority=50)

    logger.info("Jarvis Neural Connection wired to event bus (3 event types)")
    return jarvis_conn


__all__ = [
    "JarvisNeuralConnection",
    "JarvisProactiveSuggestion",
    "RecommendedAction",
    "AnomalyType",
    "RecommendationType",
    "wire_jarvis_neural_connection",
]
