"""QuantStats-style tearsheet: Omega, CVaR, tail ratio, ulcer, recovery."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.domain.quant.tearsheet import compute_tearsheet


def test_tearsheet_empty_returns_are_zero():
    out = compute_tearsheet([])
    assert out["omega_ratio"] == 0.0
    assert out["cvar_95"] == 0.0
    assert out["tail_ratio"] == 0.0
    assert out["ulcer_index"] == 0.0
    assert out["recovery_factor"] == 0.0


def test_tearsheet_omega_is_gains_over_losses():
    returns = [0.02, 0.01, -0.01, 0.03, -0.02]
    out = compute_tearsheet(returns, threshold=0.0)
    gains = sum(r for r in returns if r > 0)
    losses = abs(sum(r for r in returns if r < 0))
    assert math.isclose(out["omega_ratio"], gains / losses, rel_tol=1e-9)


def test_tearsheet_cvar_is_mean_of_worst_5_percent():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.001, 0.01, 200).tolist()
    out = compute_tearsheet(returns)
    arr = np.asarray(returns, dtype=float)
    cutoff = float(np.quantile(arr, 0.05))
    expected = float(arr[arr <= cutoff].mean())
    assert math.isclose(out["cvar_95"], expected, rel_tol=1e-9)
    assert out["var_95"] <= 0 or abs(out["var_95"] - cutoff) < 1e-12


def test_tearsheet_tail_ratio_uses_95_vs_5():
    returns = [-0.08, -0.02, 0.0, 0.01, 0.06]
    out = compute_tearsheet(returns)
    p95 = float(np.percentile(returns, 95))
    p5 = float(np.percentile(returns, 5))
    expected = abs(p95) / abs(p5)
    assert math.isclose(out["tail_ratio"], expected, rel_tol=1e-9)


def test_tearsheet_ulcer_and_recovery_from_drawdown():
    equity = [100.0, 110.0, 99.0, 105.0]
    returns = np.diff(equity) / np.array(equity[:-1])
    out = compute_tearsheet(returns.tolist())
    peak = np.maximum.accumulate(equity)
    dd = (np.array(equity) - peak) / peak
    ulcer = float(np.sqrt(np.mean(np.square(dd))))
    assert math.isclose(out["ulcer_index"], ulcer, rel_tol=1e-6)
    assert out["recovery_factor"] > 0


def test_tearsheet_monthly_returns_when_dates_given():
    idx = [
        pd.Timestamp("2024-01-31"),
        pd.Timestamp("2024-02-29"),
        pd.Timestamp("2024-03-31"),
    ]
    returns = [0.02, -0.01, 0.03]
    out = compute_tearsheet(returns, dates=idx)
    assert "2024-01" in out["monthly_returns"]
    assert len(out["monthly_returns"]) == 3
