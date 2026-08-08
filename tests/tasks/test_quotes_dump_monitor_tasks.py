"""Quotes dump monitor tick + optional auto-dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock


def test_quotes_dump_monitor_below_threshold(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 0, "backend": "memory"},
    )
    monkeypatch.setattr(
        "app.tasks.quotes_dump_monitor_tasks.get_runtime_int",
        lambda key, default=0: 2 if "THRESHOLD" in key else default,
    )
    from app.tasks.quotes_dump_monitor_tasks import run_quotes_dump_monitor

    out = run_quotes_dump_monitor(auto_dispatch=True)
    assert out["ok"] is True
    assert out["warn"] is False
    assert out["skipped"] is True
    assert out["dispatched"] is False


def test_quotes_dump_monitor_warn_without_auto_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 5, "backend": "memory"},
    )
    monkeypatch.setattr(
        "app.tasks.quotes_dump_monitor_tasks.get_runtime_int",
        lambda key, default=0: 1 if "THRESHOLD" in key else default,
    )
    from app.tasks.quotes_dump_monitor_tasks import run_quotes_dump_monitor

    out = run_quotes_dump_monitor(auto_dispatch=False)
    assert out["warn"] is True
    assert out["dispatched"] is False
    assert out["reason"] == "warn_without_auto_dispatch"
    assert out["preferred_endpoint"] == "quotes/page"


def test_quotes_dump_monitor_auto_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 3, "backend": "memory"},
    )
    monkeypatch.setattr(
        "app.tasks.quotes_dump_monitor_tasks.get_runtime_int",
        lambda key, default=0: 1 if "THRESHOLD" in key else default,
    )
    fake = MagicMock(return_value={"ok": True, "sent": 1, "quotes_dump": {"warn": True}})
    monkeypatch.setattr(
        "app.tasks.alert_dispatch_tasks.run_dispatch_alert_notifications",
        fake,
    )
    from app.tasks.quotes_dump_monitor_tasks import run_quotes_dump_monitor

    out = run_quotes_dump_monitor(auto_dispatch=True)
    assert out["warn"] is True
    assert out["dispatched"] is True
    assert out["reason"] == "auto_dispatched"
    fake.assert_called_once()
