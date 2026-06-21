"""Tests for VectorBT optional backtest adapter."""

from __future__ import annotations

import pandas as pd
import pytest

from app.modules.strategy.services.strategy.vectorbt_adapter import VectorBTBacktestAdapter


@pytest.fixture
def sample_close() -> pd.Series:
    return pd.Series([100.0, 101.0, 102.0, 101.5, 103.0])


def test_not_available_returns_flag(sample_close: pd.Series):
    adapter = VectorBTBacktestAdapter()
    if adapter.is_available():
        pytest.skip("vectorbt installed in environment")
    out = adapter.compare_with_fast_preview(close=sample_close, fast_metrics={"sharpe_ratio": 1.0})
    assert out["available"] is False
    assert out["reason"] == "vectorbt_not_installed"


def test_compare_structure_when_unavailable(sample_close: pd.Series):
    adapter = VectorBTBacktestAdapter()
    out = adapter.compare_with_fast_preview(close=sample_close, fast_metrics={"expected_return": "5%"})
    assert "fast" in out
    if not adapter.is_available():
        assert out["available"] is False
