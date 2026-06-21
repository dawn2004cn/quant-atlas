"""Backtest Celery task helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.errors import ValidationError
from app.tasks.backtest_tasks import run_strategy_backtest, submit_strategy_backtest


def test_run_strategy_backtest_raises_without_service(monkeypatch):
    monkeypatch.setattr(
        "app.bootstrap_components.service_wiring.get_registry",
        lambda: MagicMock(get_or_none=lambda _name: None),
    )

    with pytest.raises(ValidationError, match="Strategy service not configured"):
        run_strategy_backtest(
            symbol="600519",
            strategy_name="MA",
            start="2024-01-01",
            end="2024-06-01",
        )


def test_submit_strategy_backtest_sync_mode(monkeypatch):
    monkeypatch.setattr("app.tasks.backtest_tasks.run_strategy_backtest_task", None)
    monkeypatch.setattr(
        "app.tasks.backtest_tasks.run_strategy_backtest",
        lambda **kwargs: {"status": "ok"},
    )

    result = submit_strategy_backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
    )

    assert result["status"] == "completed"
    assert result["mode"] == "sync"
