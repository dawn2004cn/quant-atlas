from __future__ import annotations

"""Dynamic Strategy Allocation - Contextual Multi-Armed Bandit.

This module implements from strategy_plan.md:
- StrategyBandit: Dynamic weight allocation based on performance
- MetaStrategy: Agent for fund allocation across sub-strategies
- Context-aware: Adjust weights based on market regime

Usage:
    allocator = StrategyAllocator()
    weights = allocator.allocate(context={"regime": "bear", "volatility": "high"})
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""
    strategy_name: str
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    trade_count: int = 0
    recent_returns: list[float] = field(default_factory=list)
    regime_performance: dict[str, float] = field(default_factory=dict)


@dataclass
class AllocationDecision:
    """Decision on fund allocation."""
    timestamp: datetime
    regime: str
    allocations: dict[str, float]
    rationale: str


class ContextualBandit:
    """Contextual Multi-Armed Bandit for strategy allocation.

    Uses historical performance to dynamically adjust weights.
    """

    def __init__(
        self,
        exploration_rate: float = 0.1,
        learning_rate: float = 0.1,
    ):
        self._exploration_rate = exploration_rate
        self._learning_rate = learning_rate
        self._strategy_performance: dict[str, StrategyPerformance] = {}

    def record_performance(
        self,
        strategy_name: str,
        return_value: float,
        regime: str = "neutral",
    ) -> None:
        """Record strategy performance."""
        if strategy_name not in self._strategy_performance:
            self._strategy_performance[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name
            )

        perf = self._strategy_performance[strategy_name]
        perf.recent_returns.append(return_value)
        if len(perf.recent_returns) > 30:
            perf.recent_returns = perf.recent_returns[-30:]

        if regime not in perf.regime_performance:
            perf.regime_performance[regime] = 0.0

        perf.regime_performance[regime] = (
            perf.regime_performance[regime] * 0.9 + return_value * 0.1
        )

    def calculate_weights(
        self,
        context: dict[str, Any],
    ) -> dict[str, float]:
        """Calculate allocation weights based on context."""
        regime = context.get("regime", "neutral")

        weights = {}
        total_score = 0.0

        for name, perf in self._strategy_performance.items():
            regime_return = perf.regime_performance.get(regime, 0.0)
            recent_return = sum(perf.recent_returns[-5:]) / 5 if perf.recent_returns else 0.0

            score = regime_return * 0.7 + recent_return * 0.3

            if self._exploration_rate > 0:
                import random
                score += random.uniform(0, self._exploration_rate)

            weights[name] = max(0.0, score)
            total_score += weights[name]

        if total_score > 0:
            for name in weights:
                weights[name] = weights[name] / total_score
        else:
            equal_weight = 1.0 / len(self._strategy_performance) if self._strategy_performance else 1.0
            for name in self._strategy_performance:
                weights[name] = equal_weight

        return weights


class MetaStrategy:
    """Meta-strategy Agent for fund allocation.

    Monitors sub-strategies and allocates funds dynamically.
    """

    def __init__(self, bandit: ContextualBandit | None = None):
        self._bandit = bandit or ContextualBandit()
        self._allocation_history: list[AllocationDecision] = []

    def allocate(
        self,
        strategies: list[str],
        context: dict[str, Any],
    ) -> dict[str, float]:
        """Allocate funds across strategies based on context."""
        for strategy in strategies:
            if strategy not in self._bandit._strategy_performance:
                self._bandit._strategy_performance[strategy] = StrategyPerformance(
                    strategy_name=strategy
                )

        weights = self._bandit.calculate_weights(context)

        decision = AllocationDecision(
            timestamp=datetime.now(),
            regime=context.get("regime", "unknown"),
            allocations=weights,
            rationale=self._generate_rationale(weights, context),
        )
        self._allocation_history.append(decision)

        logger.info(f"Meta-strategy allocation: {weights}")
        return weights

    def _generate_rationale(
        self,
        weights: dict[str, float],
        context: dict[str, Any],
    ) -> str:
        """Generate explanation for allocation decision."""
        regime = context.get("regime", "neutral")
        top_strategies = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:2]

        rationale = f"Based on {regime} regime: "
        rationale += ", ".join([f"{s}:{w:.1%}" for s, w in top_strategies])

        return rationale

    def record_outcome(
        self,
        strategy_name: str,
        return_value: float,
        regime: str,
    ) -> None:
        """Record outcome for learning."""
        self._bandit.record_performance(strategy_name, return_value, regime)

    def get_allocation_history(self) -> list[AllocationDecision]:
        """Get allocation history."""
        return self._allocation_history.copy()


class EnsembleAllocator:
    """Ensemble allocator combining multiple strategies.

    Works with existing HolyGrailEnsembleEngine.
    """

    def __init__(self, meta_strategy: MetaStrategy | None = None):
        self._meta = meta_strategy or MetaStrategy()
        self._base_weights: dict[str, float] = {}

    def set_base_weights(self, weights: dict[str, float]) -> None:
        """Set base weights for strategies."""
        self._base_weights = weights

    def compute_ensemble_weights(
        self,
        strategies: list[str],
        context: dict[str, Any],
    ) -> dict[str, float]:
        """Compute ensemble weights combining base and dynamic."""
        dynamic_weights = self._meta.allocate(strategies, context)

        if not self._base_weights:
            return dynamic_weights

        final_weights = {}
        for strategy in strategies:
            base = self._base_weights.get(strategy, 0.0)
            dynamic = dynamic_weights.get(strategy, 0.0)
            final_weights[strategy] = base * 0.3 + dynamic * 0.7

        total = sum(final_weights.values())
        if total > 0:
            final_weights = {k: v / total for k, v in final_weights.items()}

        return final_weights


_global_allocator: EnsembleAllocator | None = None


def get_strategy_allocator() -> EnsembleAllocator:
    """Get singleton strategy allocator."""
    global _global_allocator
    if _global_allocator is None:
        _global_allocator = EnsembleAllocator()
    return _global_allocator
