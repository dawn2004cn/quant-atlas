"""Shared MLflow backtest hook."""

from __future__ import annotations

from app.facade.dto.backtest_facade_dto import BacktestResultDTO
from app.infrastructure.mlflow.backtest_log_hook import attach_mlflow_run_id


def test_attach_mlflow_run_id_sets_field(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.backtest_log_hook.ModelRegistry.log_backtest",
        staticmethod(
            lambda *_args, **_kwargs: {
                "run_id": "run-xyz",
                "experiment_id": "1",
                "ui_url": "http://mlflow/#/experiments/1/runs/run-xyz",
                "model_name": "MA-600519",
                "model_version": "3",
            }
        ),
    )
    dto = BacktestResultDTO(symbol="600519", strategy_name="MA", sharpe=1.2)
    payload = attach_mlflow_run_id(
        dto,
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-12-31",
        initial_capital=100000,
    )
    assert payload["mlflow_run_id"] == "run-xyz"
    assert payload["mlflow_model_name"] == "MA-600519"
    assert payload["mlflow_model_version"] == "3"
    assert payload["sharpe"] == 1.2
