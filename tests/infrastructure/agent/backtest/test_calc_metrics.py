"""Backtest metrics financial formula tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.metrics import calc_metrics


def test_calc_metrics_sortino_uses_full_sample_downside_deviation():
  """Sortino denominator must use all periods, not only negative-return bars."""
  # Two negative days, eight flat — old code inflated downside std.
  equity = pd.Series(
      [100.0, 99.0, 98.0] + [98.0] * 7,
      index=pd.date_range("2024-01-01", periods=10, freq="D"),
  )
  m = calc_metrics(equity, trades=[], initial_cash=100.0, bars_per_year=252)
  port_ret = equity.pct_change().fillna(0.0)
  downside = np.minimum(port_ret.to_numpy(dtype=float), 0.0)
  expected_dd = float(np.sqrt((downside ** 2).sum() / len(port_ret)))
  expected_sortino = float(port_ret.mean() / (expected_dd + 1e-10) * np.sqrt(252))
  assert m["sortino"] == round(expected_sortino, 4)


def test_calc_metrics_sharpe_uses_sample_std():
    equity = pd.Series(
        [100.0, 101.0, 102.0, 101.5, 103.0],
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    m = calc_metrics(equity, trades=[], initial_cash=100.0, bars_per_year=252)
    port_ret = equity.pct_change().fillna(0.0)
    vol = float(port_ret.std(ddof=1))
    expected = float(port_ret.mean() / (vol + 1e-10) * np.sqrt(252))
    assert m["sharpe"] == m["sharpe_ratio"]
    assert abs(m["sharpe"] - expected) < 1e-9


def test_calc_metrics_sharpe_subtracts_risk_free(monkeypatch):
    monkeypatch.setenv("BT_RISK_FREE_ANNUAL", "0.02")
    import app.core.runtime_config as runtime_config

    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)
    equity = pd.Series(
        [100.0, 101.0, 102.0, 103.0, 104.0],
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    m = calc_metrics(equity, trades=[], initial_cash=100.0, bars_per_year=252)
    port_ret = equity.pct_change().fillna(0.0)
    vol = float(port_ret.std(ddof=1))
    rf_per_bar = (1.02 ** (1 / 252)) - 1
    expected = float((port_ret.mean() - rf_per_bar) / (vol + 1e-10) * np.sqrt(252))
    assert abs(m["sharpe"] - expected) < 1e-6


def test_calc_metrics_max_drawdown_pct_is_positive_display():
    equity = pd.Series(
        [100.0, 110.0, 99.0, 105.0],
        index=pd.date_range("2024-01-01", periods=4, freq="D"),
    )
    m = calc_metrics(equity, trades=[], initial_cash=100.0, bars_per_year=252)
    assert m["max_drawdown"] < 0
    assert m["max_drawdown_pct"] > 0
    assert abs(m["max_drawdown_pct"] - abs(m["max_drawdown"]) * 100) < 1e-9
