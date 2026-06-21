"""因子 IC 巡检任务（无 Celery 时亦可测 run_factor_ic_monitor）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def rd_off(monkeypatch):
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")


@pytest.fixture
def rd_on(monkeypatch):
    monkeypatch.setenv("ENABLE_RD_AGENT", "1")


def test_run_factor_ic_monitor_skips_when_rd_disabled(rd_off) -> None:
    from app.tasks.factor_ic_alerts import run_factor_ic_monitor

    out = run_factor_ic_monitor()
    assert out.get("skipped") is True
    assert "ENABLE_RD_AGENT" in str(out.get("reason", ""))


def test_run_factor_ic_monitor_weak_signals_push_and_suppress(rd_on, monkeypatch) -> None:
    summary = {
        "weak_ic_lag1_count": 2,
        "mean_abs_ic_lag1": 0.03,
        "ic_warn_threshold": 0.05,
        "factors_with_ic_decay": 2,
        "alerts": [{"message": "m1"}, {"message": "m2"}],
    }
    pushed: list[dict] = []

    def fake_push(**kwargs):
        pushed.append(kwargs)

    class _FakeSvc:
        def monitor_summary(self, **kwargs):
            return summary

    monkeypatch.setattr("app.tasks.factor_ic_alerts.FactorCatalogService", lambda base_dir: _FakeSvc())
    monkeypatch.setenv("FACTOR_IC_WARN", "0.05")

    with patch("app.tasks.factor_ic_alerts.get_task_message_store") as gms:
        gms.return_value.push = fake_push
        from app.tasks.factor_ic_alerts import run_factor_ic_monitor

        out = run_factor_ic_monitor()

    assert out.get("weak_ic_lag1_count") == 2
    assert out.get("_suppress_default_task_message") is True
    assert len(pushed) == 1
    assert pushed[0]["event"] == "factor_ic_alert"


def test_run_factor_ic_monitor_no_weak_no_push(rd_on, monkeypatch) -> None:
    summary = {
        "weak_ic_lag1_count": 0,
        "mean_abs_ic_lag1": 0.12,
        "ic_warn_threshold": 0.05,
        "factors_with_ic_decay": 3,
        "alerts": [],
    }
    pushed: list[dict] = []

    class _FakeSvc:
        def monitor_summary(self, **kwargs):
            return summary

    monkeypatch.setattr("app.tasks.factor_ic_alerts.FactorCatalogService", lambda base_dir: _FakeSvc())
    monkeypatch.setenv("FACTOR_IC_WARN", "0.05")

    with patch("app.tasks.factor_ic_alerts.get_task_message_store") as gms:
        gms.return_value.push = lambda **k: pushed.append(k)
        from app.tasks.factor_ic_alerts import run_factor_ic_monitor

        out = run_factor_ic_monitor()

    assert pushed == []
    assert out.get("skipped") is True
    assert "_suppress_default_task_message" not in out or not out.get("_suppress_default_task_message")
