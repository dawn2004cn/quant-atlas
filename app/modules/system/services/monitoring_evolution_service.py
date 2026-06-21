"""Monitoring & Evolution — Concept drift detection, deep attribution, auto rebalancing, RLHF for trading."""

from __future__ import annotations

import json
import math
import statistics
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConceptDriftReport:
    """Concept drift detection result."""
    strategy_id: str
    correlation_live_vs_backtest: float  # current correlation
    baseline_correlation: float  # expected correlation
    drift_detected: bool
    drift_severity: str  # none / mild / severe
    recommendation: str = ""


@dataclass
class DeepAttribution:
    """Deep attribution: decompose PnL into alpha, beta, slippage, luck."""
    strategy_id: str
    total_pnl: float = 0.0
    alpha_contribution: float = 0.0
    beta_contribution: float = 0.0
    slippage_cost: float = 0.0
    luck_component: float = 0.0
    residual: float = 0.0


@dataclass
class RebalanceSuggestion:
    """Auto rebalancing suggestion based on market regime."""
    strategy_id: str
    current_regime: str
    suggested_allocations: dict[str, float]  # strategy_id → weight
    reason: str = ""
    confidence: float = 0.0


@dataclass
class RLHFFeedback:
    """RLHF feedback: trade PnL as reward signal for prompt evolution."""
    cycle_id: str
    strategy_id: str
    pnl: float
    sharpe: float
    max_drawdown: float
    reward_score: float  # composite reward
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConceptDriftService:
    """Real-time concept drift detection between live and backtest signals."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "concept_drift_log.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._live_buffer: dict[str, deque[float]] = {}
        self._backtest_buffer: dict[str, deque[float]] = {}

    def feed_live_signal(self, strategy_id: str, value: float):
        """Feed a live signal value."""
        if strategy_id not in self._live_buffer:
            self._live_buffer[strategy_id] = deque(maxlen=252)
        self._live_buffer[strategy_id].append(value)

    def feed_backtest_signal(self, strategy_id: str, value: float):
        """Feed a backtest signal value."""
        if strategy_id not in self._backtest_buffer:
            self._backtest_buffer[strategy_id] = deque(maxlen=252)
        self._backtest_buffer[strategy_id].append(value)

    def detect_drift(self, strategy_id: str, window: int = 60) -> ConceptDriftReport:
        """Detect concept drift between live and backtest signals."""
        live = list(self._live_buffer.get(strategy_id, deque()))[-window:]
        bt = list(self._backtest_buffer.get(strategy_id, deque()))[-window:]

        n = min(len(live), len(bt))
        if n < 10:
            return ConceptDriftReport(
                strategy_id=strategy_id,
                correlation_live_vs_backtest=0,
                baseline_correlation=0.8,
                drift_detected=False,
                drift_severity="none",
                recommendation="样本不足，无法检测漂移",
            )

        live = live[-n:]
        bt = bt[-n:]

        # Pearson correlation
        mean_l = statistics.mean(live)
        mean_b = statistics.mean(bt)
        cov = sum((live[i] - mean_l) * (bt[i] - mean_b) for i in range(n))
        var_l = sum((x - mean_l) ** 2 for x in live)
        var_b = sum((x - mean_b) ** 2 for x in bt)
        corr = cov / (math.sqrt(var_l) * math.sqrt(var_b)) if var_l > 0 and var_b > 0 else 0

        baseline = 0.8
        drift = abs(corr) < baseline * 0.7

        if drift:
            severity = "severe" if abs(corr) < 0.3 else "mild"
            recommendation = "策略可能失效，建议触发 PromptEvolution 重新优化" if severity == "severe" else "信号偏差较大，建议检查参数"
        else:
            severity = "none"
            recommendation = "信号稳定，无需调整"

        report = ConceptDriftReport(
            strategy_id=strategy_id,
            correlation_live_vs_backtest=round(corr, 4),
            baseline_correlation=baseline,
            drift_detected=drift,
            drift_severity=severity,
            recommendation=recommendation,
        )
        self._persist(report)
        return report

    def _persist(self, report: ConceptDriftReport):
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report.__dict__, ensure_ascii=False) + "\n")


class DeepAttributionService:
    """Decompose PnL into alpha, beta, slippage, and luck components."""

    def attribute(self, strategy_id: str, total_pnl: float, market_return: float,
                  strategy_beta: float, estimated_slippage: float,
                  expected_alpha: float) -> DeepAttribution:
        """Decompose PnL into components."""
        beta_contrib = market_return * strategy_beta
        alpha_contrib = total_pnl - beta_contrib - estimated_slippage
        luck_contrib = max(0, alpha_contrib - expected_alpha) if expected_alpha > 0 else 0
        residual = total_pnl - alpha_contrib - beta_contrib - estimated_slippage - luck_contrib

        return DeepAttribution(
            strategy_id=strategy_id,
            total_pnl=round(total_pnl, 4),
            alpha_contribution=round(alpha_contrib, 4),
            beta_contribution=round(beta_contrib, 4),
            slippage_cost=round(estimated_slippage, 4),
            luck_component=round(luck_contrib, 4),
            residual=round(residual, 4),
        )


class AutoRebalanceService:
    """Auto rebalancing suggestions based on market regime."""

    def suggest(self, strategy_id: str, current_regime: str,
                strategy_performances: dict[str, float]) -> RebalanceSuggestion:
        """Suggest allocation adjustments based on regime."""
        regime_weights = {
            "bull": {"momentum": 0.4, "breakout": 0.3, "mean_reversion": 0.1, "defensive": 0.2},
            "bear": {"momentum": 0.1, "breakout": 0.1, "mean_reversion": 0.3, "defensive": 0.5},
            "sideways": {"momentum": 0.2, "breakout": 0.2, "mean_reversion": 0.4, "defensive": 0.2},
            "extreme": {"momentum": 0.05, "breakout": 0.05, "mean_reversion": 0.2, "defensive": 0.7},
        }

        weights = regime_weights.get(current_regime, regime_weights["sideways"])
        # Adjust based on recent performance
        for sid, perf in strategy_performances.items():
            if sid in weights:
                if perf > 0:
                    weights[sid] *= (1 + perf * 0.5)
                else:
                    weights[sid] *= (1 + perf * 0.3)

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return RebalanceSuggestion(
            strategy_id=strategy_id,
            current_regime=current_regime,
            suggested_allocations=weights,
            reason=f"根据 {current_regime} 市场环境自动调整策略权重",
            confidence=0.85 if current_regime in ("bull", "bear") else 0.7,
        )


class RLHFTradingService:
    """RLHF for trading: PnL as reward signal for prompt evolution."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "rlhf_feedback.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def compute_reward(self, strategy_id: str, pnl: float, sharpe: float, max_drawdown: float) -> RLHFFeedback:
        """Compute composite reward score from trading metrics."""
        # Reward = normalized PnL + sharpe bonus - drawdown penalty
        pnl_score = max(-1, min(1, pnl * 10))  # normalize to [-1, 1]
        sharpe_score = max(0, min(1, sharpe / 3))  # sharpe 3 = max
        dd_penalty = max(0, min(1, abs(max_drawdown) * 5))  # 20% drawdown = max penalty

        reward = pnl_score * 0.5 + sharpe_score * 0.3 - dd_penalty * 0.2

        feedback = RLHFFeedback(
            cycle_id=f"rlhf.{uuid.uuid4().hex[:8]}",
            strategy_id=strategy_id,
            pnl=round(pnl, 4),
            sharpe=round(sharpe, 4),
            max_drawdown=round(max_drawdown, 4),
            reward_score=round(reward, 4),
        )
        self._persist(feedback)
        return feedback

    def feed_to_prompt_evolution(self, feedback: RLHFFeedback):
        """Send RLHF feedback to PromptEvolutionService."""
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
            evo = PromptEvolutionService()
            evo.record_feedback(
                prompt_id=feedback.strategy_id,
                rating=max(0, min(1, (feedback.reward_score + 1) / 2)),  # normalize to 0..1
                context={"pnl": feedback.pnl, "sharpe": feedback.sharpe, "source": "rlhf"},
            )
            logger.info("RLHF feedback fed to PromptEvolution for %s (reward=%.4f)",
                       feedback.strategy_id, feedback.reward_score)
        except Exception as exc:
            logger.warning("RLHF → PromptEvolution failed: %s", exc)

    def _persist(self, feedback: RLHFFeedback):
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(feedback.__dict__, ensure_ascii=False) + "\n")
