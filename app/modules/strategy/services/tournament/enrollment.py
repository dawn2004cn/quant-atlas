"""Tournament candidate enrollment helpers (MCP / API shared)."""

from __future__ import annotations

from typing import Any, Mapping

from app.core.logger import get_logger
from app.modules.strategy.services.tournament.strategy_tournament_service import (
    StrategyTournamentService,
    TournamentCandidate,
    TournamentVerdict,
)

logger = get_logger(__name__)


def enroll_tournament_candidate(
    *,
    strategy_id: str,
    sharpe: float,
    max_drawdown: float,
    bias_passed: bool,
    win_rate: float | None = None,
    total_return: float = 0.0,
    sample_start: str | None = None,
    sample_end: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    service: StrategyTournamentService | None = None,
) -> TournamentVerdict:
    """Evaluate and optionally promote a candidate (bias + Sharpe/MDD gates)."""
    meta = dict(metadata or {})
    meta.setdefault("total_return", total_return)
    if sample_start:
        meta.setdefault("sample_start", sample_start)
    if sample_end:
        meta.setdefault("sample_end", sample_end)
    candidate = TournamentCandidate(
        strategy_id=strategy_id,
        sharpe=float(sharpe),
        max_drawdown=abs(float(max_drawdown)),
        win_rate=win_rate,
        bias_passed=bool(bias_passed),
        metadata=meta,
    )
    svc = service or StrategyTournamentService()
    verdict = svc.evaluate(candidate)
    logger.info(
        "enroll_tournament strategy=%s accepted=%s reason=%s",
        strategy_id,
        verdict.accepted,
        verdict.reason,
    )
    return verdict
