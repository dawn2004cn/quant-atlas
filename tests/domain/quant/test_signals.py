"""Shared strategy signals must react to parameters, not buy-and-hold."""

from __future__ import annotations

from app.domain.quant.signals import strategy_returns


def _buy_hold(prices: list[float]) -> list[float]:
    return strategy_returns(prices, {}, "buy_hold")


def test_ma_cross_differs_from_buy_hold():
    prices = [10.0] * 30 + [20.0] * 30
    ma = strategy_returns(prices, {"fast_ma": 5, "slow_ma": 20}, "trend_following_basic")
    assert len(ma) == len(prices)
    assert ma != _buy_hold(prices)


def test_different_ma_windows_change_returns():
    prices = [100.0 + i for i in range(40)] + [140.0 - i for i in range(40)]
    a = strategy_returns(prices, {"fast_ma": 3, "slow_ma": 10}, "trend_following_basic")
    b = strategy_returns(prices, {"fast_ma": 8, "slow_ma": 25}, "trend_following_basic")
    assert a != b


def test_auto_detects_rsi_from_params():
    prices = list(range(50, 10, -1)) + list(range(10, 40))
    rets = strategy_returns(prices, {"rsi_period": 5, "oversold": 30, "overbought": 70})
    assert any(x != 0 for x in rets)


def test_period_param_is_momentum_lookback():
    prices = [10.0, 10.5, 10.2, 11.0, 10.8, 12.0, 11.5, 13.0]
    a = strategy_returns(prices, {"period": 2})
    b = strategy_returns(prices, {"period": 5})
    assert a != b
