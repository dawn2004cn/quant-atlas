"""Phase 32: Celery autodiscover + worker STRICT config validation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.bootstrap_components.runtime_config_validator import validate_worker_runtime_config


def test_celery_autodiscover_registers_market_task() -> None:
    from app.celery_app import celery_app

    assert celery_app is not None
    assert "app.tasks.market_tasks.scheduled_longhu" in celery_app.tasks


def test_celery_autodiscover_registers_factor_lifecycle_tasks() -> None:
    from app.celery_app import celery_app

    assert celery_app is not None
    assert "factor.lifecycle_daily_check" in celery_app.tasks


def test_validate_worker_runtime_config_skips_without_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STRICT_BOOTSTRAP", raising=False)
    assert validate_worker_runtime_config() is None


def test_validate_worker_runtime_config_runs_when_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRICT_BOOTSTRAP", "1")
    settings = SimpleNamespace(
        use_mysql=False,
        mysql=None,
        database_uri="sqlite:///tmp/test.db",
        enable_celery=False,
        celery_broker_url="redis://192.168.8.103:6380/0",
        tdx_root_path=None,
        qmt=SimpleNamespace(enabled=False, qmt_path=None, account_id=None),
    )
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: settings,
    )
    report = validate_worker_runtime_config()
    assert report is not None
    assert report.ok
