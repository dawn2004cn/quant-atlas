from __future__ import annotations

"""Monte Carlo engines for Hyper-Simulator — trade permutation + GBM price paths."""

from typing import Any

import numpy as np


def monte_carlo_permutation(
    pnls: list[float],
    *,
    initial_capital: float,
    n_simulations: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Shuffle trade PnL order to test path significance (no external backtest dep)."""
    if len(pnls) < 3:
        return {
            "error": "need_at_least_3_trades",
            "p_value_sharpe": 1.0,
            "n_trades": len(pnls),
            "n_simulations": n_simulations,
        }

    arr = np.array(pnls, dtype=float)
    actual = _path_metrics(arr, initial_capital)
    rng = np.random.default_rng(seed)
    sharpe_hits = 0
    dd_hits = 0
    sim_sharpes: list[float] = []

    for _ in range(n_simulations):
        shuffled = rng.permutation(arr)
        sim = _path_metrics(shuffled, initial_capital)
        sim_sharpes.append(sim["sharpe"])
        if sim["sharpe"] >= actual["sharpe"]:
            sharpe_hits += 1
        if sim["max_dd"] >= actual["max_dd"]:
            dd_hits += 1

    sim_arr = np.array(sim_sharpes)
    return {
        "actual_sharpe": round(actual["sharpe"], 4),
        "actual_max_dd": round(actual["max_dd"], 4),
        "p_value_sharpe": round(sharpe_hits / n_simulations, 4),
        "p_value_max_dd": round(dd_hits / n_simulations, 4),
        "simulated_sharpe_mean": round(float(sim_arr.mean()), 4),
        "simulated_sharpe_std": round(float(sim_arr.std()), 4),
        "simulated_sharpe_p5": round(float(np.percentile(sim_arr, 5)), 4),
        "simulated_sharpe_p95": round(float(np.percentile(sim_arr, 95)), 4),
        "n_simulations": n_simulations,
        "n_trades": len(pnls),
    }


def simulate_gbm_paths(
    *,
    s0: float,
    mu: float,
    sigma: float,
    horizon_days: int,
    n_paths: int,
    seed: int = 42,
) -> dict[str, Any]:
    """Geometric Brownian Motion terminal wealth distribution."""
    if s0 <= 0 or sigma <= 0 or horizon_days < 1:
        return {"error": "invalid_gbm_params"}

    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    shocks = rng.standard_normal((n_paths, horizon_days))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * shocks
    paths = s0 * np.exp(np.cumsum(log_returns, axis=1))
    terminal = paths[:, -1]
    returns = terminal / s0 - 1.0

    var_95 = float(np.percentile(returns, 5))
    tail = returns[returns <= var_95]
    cvar_95 = float(tail.mean()) if len(tail) else var_95

    return {
        "s0": round(s0, 4),
        "mu": round(mu, 6),
        "sigma": round(sigma, 6),
        "horizon_days": horizon_days,
        "n_paths": n_paths,
        "terminal_p5": round(float(np.percentile(terminal, 5)), 2),
        "terminal_p50": round(float(np.percentile(terminal, 50)), 2),
        "terminal_p95": round(float(np.percentile(terminal, 95)), 2),
        "return_mean": round(float(returns.mean()), 4),
        "return_std": round(float(returns.std()), 4),
        "var_95": round(var_95, 4),
        "cvar_95": round(cvar_95, 4),
        "prob_loss": round(float((returns < 0).mean()), 4),
    }


def estimate_drift_vol(closes: list[float]) -> tuple[float, float]:
    """Annualised mu/sigma from daily close prices."""
    if len(closes) < 5:
        return 0.08, 0.25
    arr = np.array(closes, dtype=float)
    arr = arr[arr > 0]
    if len(arr) < 5:
        return 0.08, 0.25
    log_ret = np.diff(np.log(arr))
    mu = float(log_ret.mean() * 252)
    sigma = float(log_ret.std() * np.sqrt(252))
    return mu, max(sigma, 0.05)


def _path_metrics(pnls: np.ndarray, initial_capital: float) -> dict[str, float]:
    equity = initial_capital + np.cumsum(pnls)
    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0.0])
    std = returns.std()
    sharpe = float(returns.mean() / (std + 1e-10) * np.sqrt(252))
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(dd.min())
    return {"sharpe": sharpe, "max_dd": max_dd}


__all__ = [
    "monte_carlo_permutation",
    "simulate_gbm_paths",
    "estimate_drift_vol",
]
