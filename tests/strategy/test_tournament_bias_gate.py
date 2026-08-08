"""Tournament rejects candidates without bias clearance."""

from __future__ import annotations

from app.modules.strategy.services.tournament.offline_runner import candidate_from_nl_record
from app.modules.strategy.services.tournament.strategy_tournament_service import (
    InMemoryPaperPool,
    StrategyTournamentService,
    TournamentCandidate,
)


def test_evaluate_rejects_when_bias_not_passed():
    pool = InMemoryPaperPool()
    svc = StrategyTournamentService(paper_pool=pool)
    verdict = svc.evaluate(
        TournamentCandidate(strategy_id="s1", sharpe=2.0, max_drawdown=0.05, bias_passed=False),
    )
    assert verdict.accepted is False
    assert "bias" in verdict.reason.lower()
    assert pool.promoted == []
    assert pool.rejected


def test_evaluate_accepts_when_bias_and_gates_ok():
    pool = InMemoryPaperPool()
    svc = StrategyTournamentService(paper_pool=pool)
    verdict = svc.evaluate(
        TournamentCandidate(strategy_id="s2", sharpe=2.0, max_drawdown=0.05, bias_passed=True),
    )
    assert verdict.accepted is True
    assert pool.promoted == ["s2"]


def test_nl_record_requires_bias_passed_flag():
    c = candidate_from_nl_record(
        {
            "candidate_ready": True,
            "strategy_id": "nl.x",
            "preview_metrics": {"sharpe": 2.5, "max_drawdown": 0.04},
            "bias_passed": True,
        }
    )
    assert c is not None
    assert c.bias_passed is True

    c2 = candidate_from_nl_record(
        {
            "candidate_ready": True,
            "strategy_id": "nl.y",
            "preview_metrics": {"sharpe": 2.5, "max_drawdown": 0.04},
        }
    )
    assert c2 is not None
    assert c2.bias_passed is False
