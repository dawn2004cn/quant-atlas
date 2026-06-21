"""Unit tests for strategy models."""

import pytest
import pandas as pd
import numpy as np
from app.models.trend_breakout import MAStrategy

@pytest.fixture
def mock_history():
    """Create 100 days of mock price data."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    # Generate a trend: 50 days down, 50 days up
    prices = np.concatenate([
        np.linspace(100, 80, 50),
        np.linspace(80, 120, 50)
    ])
    return pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": prices + 1,
        "Low": prices - 1,
        "Close": prices,
        "Volume": 1000000
    })

def test_ma_strategy_signals(mock_history):
    strategy = MAStrategy()
    result = strategy.generate_signals(mock_history.copy())
    
    assert "Signal" in result.columns
    # Check if we have at least one buy signal (1) due to the upward trend in second half
    buy_signals = result[result["Signal"] == 1]
    assert len(buy_signals) > 0
    
    # Verify the first few rows have no signal (due to MA windows)
    assert result.iloc[0]["Signal"] == 0

def test_strategy_metadata():
    strategy = MAStrategy()
    assert strategy.name is not None
    assert strategy.category == "趋势突破"
    assert len(strategy.description) > 0
