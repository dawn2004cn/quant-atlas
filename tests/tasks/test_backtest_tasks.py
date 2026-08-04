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


def test_submit_strategy_backtest_idempotent_enqueue(monkeypatch):
    apply_calls: list[dict] = []

    class _FakeTask:
        def apply_async(self, *, args=None, kwargs=None, task_id=None):
            apply_calls.append({"args": args, "kwargs": kwargs, "task_id": task_id})

            class _AR:
                id = task_id

            return _AR()

    monkeypatch.setattr("app.tasks.backtest_tasks.run_strategy_backtest_task", _FakeTask())
    monkeypatch.setattr(
        "app.infrastructure.messaging.celery_reliability.get_runtime_int",
        lambda key, default=0: 600 if "TTL" in key else 60,
    )
    # Force memory claim path (no Redis).
    monkeypatch.setattr(
        "app.infrastructure.messaging.celery_reliability._default_redis_url",
        lambda: "",
    )

    first = submit_strategy_backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
        client_idempotency_key="bt:600519:MA",
    )
    second = submit_strategy_backtest(
        symbol="600519",
        strategy_name="MA",
        start="2024-01-01",
        end="2024-06-01",
        client_idempotency_key="bt:600519:MA",
    )

    assert first["status"] == "queued"
    assert first["mode"] == "async"
    assert first["deduplicated"] is False
    assert second["task_id"] == first["task_id"]
    assert second["deduplicated"] is True
    assert len(apply_calls) == 1
