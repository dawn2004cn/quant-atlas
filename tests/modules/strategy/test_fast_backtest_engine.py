"""FastBacktestEngine must apply template signals, not buy-and-hold."""

from __future__ import annotations

import pandas as pd

from app.modules.strategy.services.strategy.fast_backtest_engine import FastBacktestEngine


def _close_df(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": values})


def test_ma_cross_is_not_buy_and_hold():
    engine = FastBacktestEngine(lake_manager=None)  # type: ignore[arg-type]
    # Price stays below then jumps above slow MA
    prices = [10.0] * 30 + [20.0] * 30
    bh = _close_df(prices)["close"].pct_change().fillna(0)
    strat = engine._apply_strategy_logic(
        _close_df(prices),
        {"fast_ma": 5, "slow_ma": 20},
        "trend_following_basic",
    )
    assert len(strat) == len(bh)
    assert not strat.equals(bh)


def test_rsi_template_uses_oversold_threshold():
    engine = FastBacktestEngine(lake_manager=None)  # type: ignore[arg-type]
    prices = list(range(50, 10, -1)) + list(range(10, 40))
    strat = engine._apply_strategy_logic(
        _close_df(prices),
        {"rsi_period": 5, "oversold": 30, "overbought": 70},
        "mean_reversion_rsi",
    )
    assert (strat != 0).any()


def test_unknown_template_falls_back_to_buy_and_hold():
    engine = FastBacktestEngine(lake_manager=None)  # type: ignore[arg-type]
    df = _close_df([10.0, 11.0, 12.0, 11.5])
    strat = engine._apply_strategy_logic(df, {}, "unknown_template")
    expected = df["close"].pct_change().fillna(0)
    assert list(strat.round(8)) == list(expected.round(8))
