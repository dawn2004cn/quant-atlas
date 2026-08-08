"""Tests for strategy tournament offline runner."""

from __future__ import annotations

from app.modules.strategy.services.tournament.offline_runner import (
    candidate_from_nl_record,
    run_tournament_batch,
)
from app.modules.strategy.services.tournament.strategy_tournament_service import (
    InMemoryPaperPool,
    StrategyTournamentService,
)


def test_candidate_from_nl_record_skips_not_ready():
    c = candidate_from_nl_record(
        {
            "strategy_id": "nl.x",
            "candidate_ready": False,
            "preview_metrics": {"estimated_sharpe": 2.0, "max_drawdown": 0.05},
        }
    )
    assert c is None


def test_candidate_from_nl_record_ready():
    c = candidate_from_nl_record(
        {
            "strategy_id": "nl.ok",
            "candidate_ready": True,
            "preview_metrics": {"estimated_sharpe": 2.1, "max_drawdown": 0.04},
        }
    )
    assert c is not None
    assert c.strategy_id == "nl.ok"
    assert c.sharpe == 2.1
    assert c.bias_passed is False


def test_run_tournament_batch_promotes_passing():
    pool = InMemoryPaperPool()
    svc = StrategyTournamentService(paper_pool=pool)
    out = run_tournament_batch(
        [
            {
                "strategy_id": "nl.a",
                "candidate_ready": True,
                "bias_passed": True,
                "preview_metrics": {"estimated_sharpe": 2.0, "max_drawdown": 0.05, "total_return": 0.15},
            },
            {
                "strategy_id": "nl.b",
                "candidate_ready": True,
                "bias_passed": True,
                "preview_metrics": {"estimated_sharpe": 1.0, "max_drawdown": 0.05},
            },
        ],
        service=svc,
    )
    assert out["accepted"] == 1
    assert out["rejected"] == 1
    assert "nl.a" in pool.promoted
