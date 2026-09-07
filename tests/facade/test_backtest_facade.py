from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.errors import ValidationError
from app.facade.backtest_facade import BacktestFacade


def test_run_backtest_delegates_and_serializes():
    strategy_service = MagicMock()
    strategy_service.backtest.return_value = {"status": "ok", "pnl": 0.12}
    facade = BacktestFacade(strategy_service=strategy_service)

    result = facade.run_backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
        initial_capital=100000,
    )

    assert result["status"] == "ok"
    strategy_service.backtest.assert_called_once()


def test_run_backtest_raises_on_service_error_dict():
    strategy_service = MagicMock()
    strategy_service.backtest.return_value = {"error": "backtest provider not available"}
    facade = BacktestFacade(strategy_service=strategy_service)

    with pytest.raises(ValidationError, match="backtest provider not available"):
        facade.run_backtest(
            symbol="600519",
            strategy_name="MA",
            start="2024-01-01",
            end="2024-06-01",
        )


def test_run_backtest_normalizes_metrics_aliases():
    strategy_service = MagicMock()
    strategy_service.backtest.return_value = {
        "status": "ok",
        "sharpe_ratio": 1.2,
        "max_drawdown_pct": -0.08,
        "winrate": 0.55,
        "equity": [{"date": "2024-01-01", "value": 1.0}],
    }
    facade = BacktestFacade(strategy_service=strategy_service)

    result = facade.run_backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
    )

    assert result["sharpe"] == 1.2
    assert result["max_drawdown"] == -0.08
    assert result["win_rate"] == 0.55
    assert len(result["equity_curve"]) == 1


def test_run_backtest_async_falls_back_to_sync(monkeypatch):
    facade = BacktestFacade(strategy_service=MagicMock())
    captured: dict = {}

    def _run(**kwargs):
        captured.update(kwargs)
        return {"status": "ok", "total_return": 0.1}

    monkeypatch.setattr("app.tasks.backtest_tasks.run_strategy_backtest_task", None)
    monkeypatch.setattr("app.tasks.backtest_tasks.run_strategy_backtest", _run)

    result = facade.run_backtest_async(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
        commission_rate=0.001,
        slippage_bps=12.0,
    )

    assert result["status"] == "completed"
    assert result["mode"] == "sync"
    assert result["result"]["status"] == "ok"
    assert captured["commission_rate"] == 0.001
    assert captured["slippage_bps"] == 12.0


def test_run_backtest_requires_strategy_service():
    facade = BacktestFacade(strategy_service=None)

    with pytest.raises(ValidationError, match="Strategy service not configured"):
        facade.run_backtest(
            symbol="600519",
            strategy_name="MA",
            start="2024-01-01",
            end="2024-06-01",
        )


def test_select_stocks_delegates_to_strategy_service():
    strategy_service = MagicMock()
    strategy_service.select_stocks.return_value = {"candidates": [{"symbol": "600519"}]}
    facade = BacktestFacade(strategy_service=strategy_service)

    result = facade.select_stocks(strategy_name="classic", market="CN", top_n=5)

    assert result["candidates"][0]["symbol"] == "600519"
    strategy_service.select_stocks.assert_called_once()
