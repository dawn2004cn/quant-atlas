"""Walk-forward grid search must score strategy params, not buy-and-hold."""

from __future__ import annotations

import pandas as pd

from app.infrastructure.strategy.walk_forward import DefaultWalkForwardOptimizer


def _price_df(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": values})


def test_evaluate_ma_params_change_score():
    prices = [100.0 + i for i in range(50)] + [150.0 - i * 0.5 for i in range(50)]
    df = _price_df(prices)
    opt = DefaultWalkForwardOptimizer()
    slow = opt._evaluate(df, {"fast_ma": 5, "slow_ma": 20}, "sharpe_ratio")
    fast = opt._evaluate(df, {"fast_ma": 2, "slow_ma": 5}, "sharpe_ratio")
    hold = opt._evaluate(df, {}, "sharpe_ratio")
    assert slow["total_return"] != hold["total_return"]
    assert slow["sharpe_ratio"] != fast["sharpe_ratio"] or slow["total_return"] != fast["total_return"]


def test_grid_search_picks_a_param_combo():
    prices = [100.0 + i * 0.4 for i in range(80)]
    df = _price_df(prices)
    opt = DefaultWalkForwardOptimizer()
    result = opt._grid_search(
        df,
        {"fast_ma": [3, 8], "slow_ma": [15, 25]},
        "sharpe_ratio",
    )
    assert result.params["fast_ma"] in (3, 8)
    assert result.params["slow_ma"] in (15, 25)
    assert result.score > -999
