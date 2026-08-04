"""Phase 41: Celery beat schedule for alert dispatch."""

from __future__ import annotations

from unittest.mock import patch


def test_beat_schedule_includes_alert_dispatch_when_enabled() -> None:
    with patch("app.celery_app.get_runtime") as mock_runtime, patch(
        "app.celery_app.get_runtime_int", side_effect=lambda key, default=0: 30 if key == "ALERT_DISPATCH_BEAT_MINUTES" else default
    ):
        def _runtime(key: str, default: str = "") -> str:
            if key == "ALERT_DISPATCH_CELERY_BEAT":
                return "1"
            if key == "ALERT_DISPATCH_MIN_LEVEL":
                return "warning"
            return default

        mock_runtime.side_effect = _runtime
        from app.celery_app import _build_beat_schedule

        beat = _build_beat_schedule()
        assert "alert-dispatch-periodic" in beat
        entry = beat["alert-dispatch-periodic"]
        assert entry["task"] == "app.tasks.alert_dispatch_tasks.dispatch_alert_notifications"
        assert entry["kwargs"]["respect_dedup"] is True


def test_beat_schedule_omits_alert_dispatch_by_default() -> None:
    with patch("app.celery_app.get_runtime") as mock_runtime:
        mock_runtime.side_effect = lambda key, default="0": default
        from app.celery_app import _build_beat_schedule

        beat = _build_beat_schedule()
        assert "alert-dispatch-periodic" not in beat
        assert "quotes-dump-monitor-periodic" not in beat


def test_beat_schedule_includes_quotes_dump_monitor_when_enabled() -> None:
    with patch("app.celery_app.get_runtime") as mock_runtime, patch(
        "app.celery_app.get_runtime_int",
        side_effect=lambda key, default=0: 15 if key == "QUOTES_DUMP_MONITOR_BEAT_MINUTES" else default,
    ):
        def _runtime(key: str, default: str = "") -> str:
            if key == "QUOTES_DUMP_MONITOR_CELERY_BEAT":
                return "1"
            return default

        mock_runtime.side_effect = _runtime
        from app.celery_app import _build_beat_schedule

        beat = _build_beat_schedule()
        assert "quotes-dump-monitor-periodic" in beat
        entry = beat["quotes-dump-monitor-periodic"]
        assert entry["task"] == "app.tasks.quotes_dump_monitor_tasks.quotes_dump_monitor_tick"
