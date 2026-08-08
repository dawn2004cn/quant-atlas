"""Offline tournament batch evaluation over NL / candidate records."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.core.logger import get_logger
from app.modules.strategy.services.tournament.strategy_tournament_service import (
    StrategyTournamentService,
    TournamentCandidate,
)

logger = get_logger(__name__)


def candidate_from_nl_record(record: Mapping[str, Any]) -> TournamentCandidate | None:
    """Build a tournament candidate from an NL strategy JSON record."""
    if not bool(record.get("candidate_ready")):
        return None
    strategy_id = str(record.get("strategy_id") or "").strip()
    if not strategy_id:
        return None
    metrics = record.get("preview_metrics") or {}
    if not isinstance(metrics, Mapping):
        metrics = {}
    sharpe = float(metrics.get("estimated_sharpe") or metrics.get("sharpe") or metrics.get("sharpe_ratio") or 0.0)
    mdd_raw = metrics.get("max_drawdown", 0.0)
    try:
        mdd = abs(float(mdd_raw))
    except (TypeError, ValueError):
        mdd = 0.0
    win_rate = metrics.get("win_rate")
    bias_passed = bool(record.get("bias_passed"))
    sample_start = metrics.get("sample_start") or record.get("sample_start")
    sample_end = metrics.get("sample_end") or record.get("sample_end")
    total_return = metrics.get("total_return") or record.get("total_return") or 0.0
    try:
        total_return_f = float(total_return)
    except (TypeError, ValueError):
        total_return_f = 0.0
    return TournamentCandidate(
        strategy_id=strategy_id,
        sharpe=sharpe,
        max_drawdown=mdd,
        win_rate=float(win_rate) if win_rate is not None else None,
        bias_passed=bias_passed,
        metadata={
            "source": "nl_record",
            "total_return": total_return_f,
            "sample_start": sample_start,
            "sample_end": sample_end,
        },
    )


def run_tournament_batch(
    records: Iterable[Mapping[str, Any]],
    *,
    service: StrategyTournamentService | None = None,
) -> dict[str, Any]:
    """Evaluate ready candidates; return accepted/rejected counts and verdicts."""
    svc = service or StrategyTournamentService()
    accepted = 0
    rejected = 0
    skipped = 0
    verdicts: list[dict[str, Any]] = []
    for row in records:
        candidate = candidate_from_nl_record(row)
        if candidate is None:
            skipped += 1
            continue
        verdict = svc.evaluate(candidate)
        verdicts.append(
            {
                "strategy_id": verdict.strategy_id,
                "accepted": verdict.accepted,
                "reason": verdict.reason,
                "bias_passed": candidate.bias_passed,
                "sharpe": candidate.sharpe,
                "max_drawdown": candidate.max_drawdown,
            }
        )
        if verdict.accepted:
            accepted += 1
        else:
            rejected += 1
    logger.info(
        "tournament_batch accepted=%s rejected=%s skipped=%s",
        accepted,
        rejected,
        skipped,
    )
    return {
        "ok": True,
        "accepted": accepted,
        "rejected": rejected,
        "skipped": skipped,
        "verdicts": verdicts,
    }
