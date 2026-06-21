"""BacktestFacade multi-strategy comparison."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.facade.backtest_facade import BacktestFacade


@pytest.fixture
def facade() -> BacktestFacade:
    svc = MagicMock()
    svc.backtest.side_effect = [
        {
            "total_return": 0.12,
            "sharpe_ratio": 1.1,
            "max_drawdown": -0.08,
            "annual_return": 0.15,
            "win_rate": 0.55,
            "trade_count": 10,
        },
        {
            "total_return": 0.08,
            "sharpe_ratio": 0.9,
            "max_drawdown": -0.05,
            "annual_return": 0.10,
            "win_rate": 0.50,
            "trade_count": 8,
        },
    ]

    fb = BacktestFacade(strategy_service=svc)
    original_run = fb.run_backtest

    def _run(**kwargs):
        raw = svc.backtest(
            symbol=kwargs["symbol"],
            strategy_name=kwargs["strategy_name"],
            start=kwargs["start"],
            end=kwargs["end"],
            initial_capital=kwargs["initial_capital"],
        )
        return {
            "status": "ok",
            "symbol": kwargs["symbol"],
            "strategy_name": kwargs["strategy_name"],
            **raw,
            "sharpe": raw.get("sharpe_ratio"),
        }

    fb.run_backtest = _run  # type: ignore[method-assign]
    return fb


def test_compare_strategies_ranks_winner(facade: BacktestFacade) -> None:
    result = facade.compare_strategies(
        symbol="600519",
        strategies=["MA", "RSI"],
        start="2024-01-01",
        end="2024-12-31",
        initial_capital=100_000,
    )

    assert result["winner"] == "MA"
    assert len(result["comparisons"]) == 2
    assert result["comparisons"][0]["status"] == "ok"
    assert result["comparisons"][0]["total_return"] == 0.12
