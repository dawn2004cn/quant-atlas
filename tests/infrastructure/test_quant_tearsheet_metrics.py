"""calc_metrics exposes QuantStats-style extras without loading the full backtest package."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd


def _load_calc_metrics():
    if "backtest" not in sys.modules:
        pkg = types.ModuleType("backtest")
        models = types.ModuleType("backtest.models")
        models.TradeRecord = type("TradeRecord", (), {})
        rf = types.ModuleType("backtest.risk_free_rate")
        rf.resolve_annual_risk_free_rate = lambda: 0.0
        sys.modules["backtest"] = pkg
        sys.modules["backtest.models"] = models
        sys.modules["backtest.risk_free_rate"] = rf

    path = Path("/workspace/app/infrastructure/agent/backtest/metrics.py")
    spec = importlib.util.spec_from_file_location("quant_atlas_backtest_metrics", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.calc_metrics


def test_calc_metrics_includes_quantstats_fields():
    calc_metrics = _load_calc_metrics()
    equity = pd.Series(
        [100.0, 102.0, 101.0, 104.0, 103.0, 106.0],
        index=pd.date_range("2024-01-01", periods=6, freq="D"),
    )
    m = calc_metrics(equity, trades=[], initial_cash=100.0, bars_per_year=252)
    for key in ("omega_ratio", "cvar_95", "tail_ratio", "ulcer_index", "recovery_factor"):
        assert key in m
        assert isinstance(m[key], float)
