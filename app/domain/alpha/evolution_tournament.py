from __future__ import annotations
"""Evolution Tournament - Resource Allocation by Performance.

Implements from strategy_plan3.md:
- Auto-allocate resources based on win rate
- Evolution ranking system
- Meta-incentives for top performers

Usage:
    tournament = EvolutionTournament()
    allocation = tournament.allocate_resources(strategy_scores)
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyScore:
    """Score for a strategy in tournament."""
    strategy_id: str
    manager_id: str
    win_rate: float
    sharpe: float
    total_return: float
    max_drawdown: float
    trades: int = 0
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceAllocation:
    """Resource allocation for strategy."""
    strategy_id: str
    manager_id: str
    compute_budget: float
    token_budget: int
    risk_budget: float
    priority: int


@dataclass
class TournamentResult:
    """Tournament result."""
    timestamp: datetime
    total_strategies: int
    rankings: list[tuple[str, float]]
    resource_changes: list[ResourceAllocation]
    promoted: list[str]
    demoted: list[str]


class EvolutionTournament:
    """Evolution tournament for resource allocation."""

    TOP_N_PROMOTE = 10
    BOTTOM_N_DEMOTE = 5
    WIN_RATE_WEIGHT = 0.4
    SHARPE_WEIGHT = 0.3
    RETURN_WEIGHT = 0.2
    DRAWDOWN_WEIGHT = 0.1

    def __init__(self):
        self._scores: dict[str, StrategyScore] = {}
        self._history: list[tuple[list[tuple[str, float]], datetime]] = []
        self._current_rankings: list[tuple[str, float]] = []

    def register_strategy(
        self,
        strategy_id: str,
        manager_id: str,
        metrics: dict[str, float],
    ) -> None:
        """Register strategy for tournament."""
        score = StrategyScore(
            strategy_id=strategy_id,
            manager_id=manager_id,
            win_rate=metrics.get("win_rate", 0.5),
            sharpe=metrics.get("sharpe", 0.0),
            total_return=metrics.get("total_return", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
            trades=int(metrics.get("trades", 0)),
        )

        self._scores[strategy_id] = score
        logger.info(f"Registered {strategy_id} for tournament")

    def update_scores(
        self,
        strategy_id: str,
        metrics: dict[str, float],
    ) -> None:
        """Update strategy scores."""
        if strategy_id not in self._scores:
            return

        score = self._scores[strategy_id]
        score.win_rate = metrics.get("win_rate", score.win_rate)
        score.sharpe = metrics.get("sharpe", score.sharpe)
        score.total_return = metrics.get("total_return", score.total_return)
        score.max_drawdown = metrics.get("max_drawdown", score.max_drawdown)
        score.trades = int(metrics.get("trades", score.trades))
        score.last_update = datetime.now()

    def calculate_rankings(
        self,
    ) -> list[tuple[str, float]]:
        """Calculate current rankings."""
        scored = []

        for strategy_id, score in self._scores.items():
            composite = self._calculate_composite(score)
            scored.append((strategy_id, composite))

        scored.sort(key=lambda x: x[1], reverse=True)
        self._current_rankings = scored

        self._history.append((scored, datetime.now()))

        return scored[:50]

    def _calculate_composite(
        self,
        score: StrategyScore,
    ) -> float:
        """Calculate composite score."""
        win_component = score.win_rate * self.WIN_RATE_WEIGHT

        sharpe_norm = min(max(score.sharpe / 2.0, 0), 1.0) * self.SHARPE_WEIGHT

        return_norm = min(max(score.total_return / 0.3, -1), 1.0)
        return_component = (return_norm + 1) * 0.5 * self.RETURN_WEIGHT

        dd_penalty = max(score.max_drawdown - 0.1, 0) * 2
        dd_component = (1 - dd_penalty) * self.DRAWDOWN_WEIGHT

        return win_component + sharpe_norm + return_component + dd_component

    def allocate_resources(
        self,
        base_compute: float = 100.0,
        base_tokens: int = 100000,
        base_risk: float = 1.0,
    ) -> list[ResourceAllocation]:
        """Allocate resources based on rankings."""
        rankings = self._current_rankings or self.calculate_rankings()

        allocations = []

        for rank, (strategy_id, score) in enumerate(rankings):
            if strategy_id not in self._scores:
                continue

            strat_score = self._scores[strategy_id]
            tier = self._get_tier(rank)

            compute = base_compute * tier
            tokens = int(base_tokens * tier)
            risk = base_risk * tier

            allocation = ResourceAllocation(
                strategy_id=strategy_id,
                manager_id=strat_score.manager_id,
                compute_budget=compute,
                token_budget=tokens,
                risk_budget=risk,
                priority=rank + 1,
            )
            allocations.append(allocation)

        logger.info(f"Allocated resources to {len(allocations)} strategies")
        return allocations

    def _get_tier(self, rank: int) -> float:
        """Get tier multiplier based on rank."""
        if rank < 10:
            return 2.0
        elif rank < 30:
            return 1.5
        elif rank < 50:
            return 1.0
        elif rank < 80:
            return 0.5
        else:
            return 0.2

    def run_tournament(
        self,
        base_compute: float = 100.0,
        base_tokens: int = 100000,
        base_risk: float = 1.0,
    ) -> TournamentResult:
        """Run full tournament cycle."""
        rankings = self.calculate_rankings()

        promoted = [sid for sid, _ in rankings[:self.TOP_N_PROMOTE]]
        demoted = [sid for sid, _ in rankings[-self.BOTTOM_N_DEMOTE:]]

        allocations = self.allocate_resources(
            base_compute, base_tokens, base_risk
        )

        return TournamentResult(
            timestamp=datetime.now(),
            total_strategies=len(self._scores),
            rankings=rankings[:10],
            resource_changes=allocations,
            promoted=promoted,
            demoted=demoted,
        )

    def get_manager_leaderboard(
        self,
    ) -> list[tuple[str, float]]:
        """Get manager-level leaderboard."""
        manager_scores: dict[str, list[float]] = defaultdict(list)

        for score in self._scores.values():
            manager_scores[score.manager_id].append(
                self._calculate_composite(score)
            )

        manager_avg = []
        for manager_id, scores in manager_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            manager_avg.append((manager_id, avg))

        manager_avg.sort(key=lambda x: x[1], reverse=True)
        return manager_avg

    def get_top_strategies(
        self,
        n: int = 10,
    ) -> list[StrategyScore]:
        """Get top N strategies."""
        rankings = self._current_rankings or self.calculate_rankings()

        top_ids = [sid for sid, _ in rankings[:n]]
        return [self._scores[sid] for sid in top_ids if sid in self._scores]


_global_tournament: EvolutionTournament | None = None


def get_tournament() -> EvolutionTournament:
    """Get global tournament."""
    global _global_tournament
    if _global_tournament is None:
        _global_tournament = EvolutionTournament()
    return _global_tournament