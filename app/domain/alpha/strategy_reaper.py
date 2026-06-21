from __future__ import annotations
"""Strategy Reaper - Automated Strategy Cleanup.

Implements from strategy_plan2.md:
- Auto-cleanup of zombie strategies (no trades 10+ days)
- Auto-cleanup of underperforming strategies (Sharpe < benchmark - 2 std)
- Manager leaderboard and meta-incentives

Usage:
    reaper = StrategyReaper()
    zombies = reaper.find_zombies(strategy_stats)
    reaper.trigger_cleanup(zombies)
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""
    strategy_id: str
    manager_id: str
    total_trades: int = 0
    last_trade_date: datetime | None = None
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    daily_returns: list[float] = field(default_factory=list)
    win_rate: float = 0.0
    avg_holding_days: float = 0.0


@dataclass
class CleanupAction:
    """Action to perform on strategy."""
    strategy_id: str
    manager_id: str
    action: str
    reason: str
    severity: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReaperReport:
    """Report from reaper run."""
    timestamp: datetime
    total_strategies: int
    zombie_count: int
    underperform_count: int
    actions: list[CleanupAction]
    leaderboard: list[tuple[str, float]]


class StrategyReaper:
    """Automated cleanup of underperforming strategies."""

    ZOMBIE_DAYS = 10
    SHARPE_ZSCORE_THRESHOLD = -2.0
    DRAWDOWN_THRESHOLD = 0.15

    def __init__(self):
        self._metrics: dict[str, StrategyMetrics] = {}
        self._cleanup_actions: list[CleanupAction] = []
        self._manager_scores: dict[str, float] = {}

    def register_strategy(self, metrics: StrategyMetrics) -> None:
        """Register strategy for monitoring."""
        self._metrics[metrics.strategy_id] = metrics
        logger.info(f"Registered {metrics.strategy_id} for reaper monitoring")

    def find_zombies(
        self,
    ) -> list[StrategyMetrics]:
        """Find zombie strategies (no trades 10+ days)."""
        cutoff = datetime.now() - timedelta(days=self.ZOMBIE_DAYS)
        zombies = []

        for metrics in self._metrics.values():
            if metrics.last_trade_date and metrics.last_trade_date < cutoff:
                zombies.append(metrics)
            elif not metrics.last_trade_date and metrics.total_trades == 0:
                zombies.append(metrics)

        logger.info(f"Found {len(zombies)} zombie strategies")
        return zombies

    def find_underperformers(
        self,
        benchmark_sharpe: float = 0.8,
    ) -> list[StrategyMetrics]:
        """Find underperforming strategies."""
        if not self._metrics:
            return []

        sharpes = [m.sharpe for m in self._metrics.values() if m.sharpe > -999]
        if not sharpes:
            return []

        mean_sharpe = sum(sharpes) / len(sharpes)
        variance = sum((s - mean_sharpe) ** 2 for s in sharpes) / len(sharpes)
        std_sharpe = variance ** 0.5

        if std_sharpe == 0:
            return []

        threshold = benchmark_sharpe + (self.SHARPE_ZSCORE_THRESHOLD * std_sharpe)

        underperformers = [
            m for m in self._metrics.values()
            if m.sharpe < threshold
        ]

        logger.info(f"Found {len(underperformers)} underperforming strategies")
        return underperformers

    def find_high_drawdown(
        self,
    ) -> list[StrategyMetrics]:
        """Find strategies with excessive drawdown."""
        high_dd = [
            m for m in self._metrics.values()
            if m.max_drawdown > self.DRAWDOWN_THRESHOLD
        ]

        logger.info(f"Found {len(high_dd)} strategies with high drawdown")
        return high_dd

    def trigger_cleanup(
        self,
        zombies: list[StrategyMetrics],
        underperformers: list[StrategyMetrics] = None,
        high_dd: list[StrategyMetrics] = None,
    ) -> list[CleanupAction]:
        """Trigger cleanup actions for flagged strategies."""
        actions = []
        underperformers = underperformers or []
        high_dd = high_dd or []

        for metrics in zombies:
            action = CleanupAction(
                strategy_id=metrics.strategy_id,
                manager_id=metrics.manager_id,
                action="FORCE_RETIRE",
                reason=f"No trades in {self.ZOMBIE_DAYS}+ days",
                severity="high",
            )
            actions.append(action)

        for metrics in underperformers:
            action = CleanupAction(
                strategy_id=metrics.strategy_id,
                manager_id=metrics.manager_id,
                action="TRIGGER_RESEARCH",
                reason=f"Sharpe {metrics.sharpe:.2f} below threshold",
                severity="medium",
            )
            actions.append(action)

        for metrics in high_dd:
            action = CleanupAction(
                strategy_id=metrics.strategy_id,
                manager_id=metrics.manager_id,
                action="PAUSE_TRADING",
                reason=f"Drawdown {metrics.max_drawdown:.2%} exceeds limit",
                severity="high",
            )
            actions.append(action)

        self._cleanup_actions.extend(actions)

        logger.info(f"Triggered {len(actions)} cleanup actions")
        return actions

    def generate_report(
        self,
        benchmark_sharpe: float = 0.8,
    ) -> ReaperReport:
        """Generate reaper report."""
        zombies = self.find_zombies()
        underperformers = self.find_underperformers(benchmark_sharpe)
        high_dd = self.find_high_drawdown()

        all_actions = self.trigger_cleanup(
            zombies, underperformers, high_dd
        )

        leaderboard = self._calculate_manager_leaderboard()

        return ReaperReport(
            timestamp=datetime.now(),
            total_strategies=len(self._metrics),
            zombie_count=len(zombies),
            underperform_count=len(underperformers),
            actions=all_actions,
            leaderboard=leaderboard,
        )

    def _calculate_manager_leaderboard(
        self,
    ) -> list[tuple[str, float]]:
        """Calculate manager performance leaderboard."""
        manager_metrics: dict[str, list[StrategyMetrics]] = {}

        for metrics in self._metrics.values():
            if metrics.manager_id not in manager_metrics:
                manager_metrics[metrics.manager_id] = []
            manager_metrics[metrics.manager_id].append(metrics)

        scores = []
        for manager_id, metrics_list in manager_metrics.items():
            avg_sharpe = sum(m.sharpe for m in metrics_list) / len(metrics_list)
            win_rate = sum(m.win_rate for m in metrics_list) / len(metrics_list)

            score = (avg_sharpe * 0.7) + (win_rate * 0.3)
            scores.append((manager_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        self._manager_scores = dict(scores)

        return scores[:10]

    def get_manager_score(
        self,
        manager_id: str,
    ) -> float:
        """Get manager performance score."""
        return self._manager_scores.get(manager_id, 0.0)

    def get_risk_budget(
        self,
        manager_id: str,
        base_budget: float = 1.0,
    ) -> float:
        """Calculate risk budget based on manager performance."""
        score = self.get_manager_score(manager_id)

        if score > 0.8:
            return base_budget * 1.5
        elif score > 0.5:
            return base_budget
        elif score > 0.3:
            return base_budget * 0.5
        else:
            return base_budget * 0.1


_global_reaper: StrategyReaper | None = None


def get_strategy_reaper() -> StrategyReaper:
    """Get global strategy reaper."""
    global _global_reaper
    if _global_reaper is None:
        _global_reaper = StrategyReaper()
    return _global_reaper