"""Core StrategyApplicationService backtest path tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService


@pytest.fixture
def strategy_svc():
    return StrategyApplicationService(
        strategy_provider=SimpleNamespace(),
        backtest_provider=MagicMock(),
        market_provider=SimpleNamespace(),
        indicator_provider=None,
    )


def test_backtest_returns_error_when_provider_missing():
    svc = StrategyApplicationService(
        strategy_provider=SimpleNamespace(),
        backtest_provider=None,
        market_provider=SimpleNamespace(),
    )
    result = svc.backtest("600519", "MA", "2024-01-01", "2024-06-01")
    assert result == {"error": "backtest provider not available"}


def test_backtest_delegates_to_provider(strategy_svc):
    strategy_svc._backtest_provider.backtest.return_value = {
        "status": "ok",
        "total_return": 0.15,
    }
    result = strategy_svc.backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
        initial_capital=50000,
    )
    assert result["status"] == "ok"
    strategy_svc._backtest_provider.backtest.assert_called_once_with(
        symbol="600519",
        strategy="MA",
        start="2024-01-01",
        end="2024-06-01",
        initial_capital=50000,
    )


def test_backtest_catches_provider_exception(strategy_svc):
    strategy_svc._backtest_provider.backtest.side_effect = RuntimeError("boom")
    result = strategy_svc.backtest("600519", "MA", "2024-01-01", "2024-06-01")
    assert "error" in result
    assert "boom" in result["error"]
