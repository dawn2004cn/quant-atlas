"""Strategy tournament service: bias + metric gates then promote to paper pool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.logger import get_logger
from app.modules.strategy.services.tournament.gates import passes_tournament_gates
from app.modules.strategy.services.tournament.paper_pool_adapter import PaperTradingPoolAdapter

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TournamentCandidate:
    strategy_id: str
    sharpe: float
    max_drawdown: float
    win_rate: float | None = None
    bias_passed: bool = False
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TournamentVerdict:
    strategy_id: str
    accepted: bool
    reason: str


class PaperPoolPort(Protocol):
    def promote(
        self,
        strategy_id: str,
        *,
        reason: str,
        metrics: dict[str, Any] | None = None,
    ) -> None: ...

    def reject(self, strategy_id: str, *, reason: str) -> None: ...


class InMemoryPaperPool:
    def __init__(self) -> None:
        self.promoted: list[str] = []
        self.rejected: list[tuple[str, str]] = []
        self.promote_metrics: list[dict[str, Any]] = []

    def promote(
        self,
        strategy_id: str,
        *,
        reason: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        self.promoted.append(strategy_id)
        self.promote_metrics.append(dict(metrics or {}))
        logger.info("tournament promote strategy=%s reason=%s", strategy_id, reason)

    def reject(self, strategy_id: str, *, reason: str) -> None:
        self.rejected.append((strategy_id, reason))
        logger.info("tournament reject strategy=%s reason=%s", strategy_id, reason)


class StrategyTournamentService:
    """Apply bias gate + SRS hard gates then update paper pool."""

    def __init__(
        self,
        *,
        paper_pool: PaperPoolPort | None = None,
        min_sharpe: float = 1.8,
        max_mdd: float = 0.12,
        require_bias_passed: bool = True,
    ) -> None:
        self._paper_pool = paper_pool or PaperTradingPoolAdapter()
        self._min_sharpe = min_sharpe
        self._max_mdd = max_mdd
        self._require_bias_passed = require_bias_passed

    def evaluate(self, candidate: TournamentCandidate) -> TournamentVerdict:
        if self._require_bias_passed and not candidate.bias_passed:
            reason = "rejected:bias_gate_not_passed"
            self._paper_pool.reject(candidate.strategy_id, reason=reason)
            return TournamentVerdict(candidate.strategy_id, False, reason)

        ok = passes_tournament_gates(
            sharpe=candidate.sharpe,
            max_drawdown=candidate.max_drawdown,
            min_sharpe=self._min_sharpe,
            max_mdd=self._max_mdd,
        )
        meta = dict(candidate.metadata or {})
        metrics = {
            "sharpe": candidate.sharpe,
            "max_drawdown": candidate.max_drawdown,
            "win_rate": candidate.win_rate,
            "total_return": float(meta.get("total_return") or 0.0),
            "sample_start": meta.get("sample_start"),
            "sample_end": meta.get("sample_end"),
            "bias_passed": True,
        }
        if ok:
            reason = (
                f"sharpe={candidate.sharpe}>{self._min_sharpe} "
                f"and mdd={candidate.max_drawdown}<{self._max_mdd}"
            )
            self._paper_pool.promote(candidate.strategy_id, reason=reason, metrics=metrics)
            return TournamentVerdict(candidate.strategy_id, True, reason)
        reason = (
            f"rejected:sharpe={candidate.sharpe},mdd={candidate.max_drawdown},"
            f"need_sharpe>{self._min_sharpe}_and_mdd<{self._max_mdd}"
        )
        self._paper_pool.reject(candidate.strategy_id, reason=reason)
        return TournamentVerdict(candidate.strategy_id, False, reason)
