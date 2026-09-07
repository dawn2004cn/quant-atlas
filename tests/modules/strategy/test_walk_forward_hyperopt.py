"""WalkForwardService.hyperopt searches real strategy params (Freqtrade-style)."""

from __future__ import annotations

from app.modules.strategy.services.simulation_service import WalkForwardService


def test_hyperopt_runs_all_grid_cells():
    svc = WalkForwardService()
    prices = [100.0 + i for i in range(120)]
    out = svc.hyperopt(
        prices,
        {"fast_ma": [5, 10], "slow_ma": [20, 30]},
        strategy="trend_following_basic",
    )
    assert out["n_trials"] == 4
    assert out["best"] is not None
    assert "out_of_sample_sharpe" in out["best"]
    assert set(out["best"]["params"]) >= {"fast_ma", "slow_ma"}


def test_validate_unchanged_on_short_series():
    svc = WalkForwardService()
    result = svc.validate("s1", [0.01, -0.01, 0.02], window_size=252)
    assert result.in_sample_sharpe == 0
    assert result.robust is False
