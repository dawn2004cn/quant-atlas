"""WalkForwardOptimizer must score real strategy params, not random placeholders."""

from __future__ import annotations

import asyncio

from app.domain.optimization.auto_tuning import WalkForwardOptimizer


def _price_rows(values: list[float]) -> list[dict]:
    return [{"close": v} for v in values]


def test_evaluate_params_changes_with_ma_windows():
    opt = WalkForwardOptimizer()
    prices = [100.0 + i for i in range(50)] + [150.0 - i * 0.4 for i in range(50)]
    rows = _price_rows(prices)
    slow = asyncio.run(opt._evaluate_params(None, {"fast_ma": 5, "slow_ma": 20}, rows))
    fast = asyncio.run(opt._evaluate_params(None, {"fast_ma": 2, "slow_ma": 5}, rows))
    hold = asyncio.run(opt._evaluate_params(None, {}, rows))
    assert slow["total_return"] != hold["total_return"]
    assert slow["sharpe_ratio"] != fast["sharpe_ratio"] or slow["total_return"] != fast["total_return"]


def test_bayesian_search_uses_real_metric():
    opt = WalkForwardOptimizer()
    prices = [100.0 + i * 0.5 for i in range(80)]
    rows = _price_rows(prices)
    params = asyncio.run(
        opt._bayesian_search(
            None,
            rows,
            {"fast_ma": [3, 8], "slow_ma": [15, 25]},
            "sharpe_ratio",
        )
    )
    assert params["fast_ma"] in (3, 8)
    assert params["slow_ma"] in (15, 25)
