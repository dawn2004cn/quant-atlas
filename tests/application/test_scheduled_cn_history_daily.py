"""收盘 A 股历史日更 Celery 任务编排."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tasks import data_backfill_tasks

pytestmark = pytest.mark.skipif(
    data_backfill_tasks.scheduled_cn_history_daily is None,
    reason="celery not installed",
)


def test_scheduled_cn_history_daily_stops_on_tdx_failure() -> None:
    svc = MagicMock()
    svc.incremental_sync_from_tdx_dayk.return_value = {"ok": False, "failed": 2}
    with patch(
        "app.tasks.data_backfill_tasks.create_tdx_dayk_sync_service",
        return_value=svc,
    ):
        out = data_backfill_tasks.scheduled_cn_history_daily()
    assert out["ok"] is False
    assert out["stage"] == "tdx_incremental"
    assert out["qlib_bin"] is None
    svc.incremental_sync_from_tdx_dayk.assert_called_once_with(
        limit=None,
        dump_qlib_bin=True,
        dump_max_workers=8,
        enable_mysql=False,
        enable_timescale=True,
        enable_csv=True,
    )


def test_scheduled_cn_history_daily_single_pass_timescale_csv_qlib() -> None:
    svc = MagicMock()
    svc.incremental_sync_from_tdx_dayk.return_value = {"ok": True, "stats": {"codes_ok": 1}}
    with patch(
        "app.tasks.data_backfill_tasks.create_tdx_dayk_sync_service",
        return_value=svc,
    ):
        out = data_backfill_tasks.scheduled_cn_history_daily()
    assert out["ok"] is True
    assert out["stage"] == "done"
    assert out["targets"] == ["timescale", "csv", "qlib"]
    svc.incremental_sync_from_tdx_dayk.assert_called_once()


def test_build_beat_includes_tdx_dayk_when_flag_on(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("QLIB_CELERY_BEAT", "0")
    monkeypatch.setenv("TDX_USE_SCHEDULED_DAILY_CHAIN", "1")
    monkeypatch.setenv("QUESTDB_SYNC_BEAT", "1")
    beat = _build_beat_schedule()
    assert "cn-history-daily-after-close" in beat
    assert beat["cn-history-daily-after-close"]["task"].endswith("scheduled_cn_history_daily")
    assert "questdb-ohlcv-after-close" not in beat
    assert "cn-history-mysql-to-qlib-after-tdx" not in beat


def test_build_beat_legacy_split_uses_csv_to_qlib(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("TDX_USE_SCHEDULED_DAILY_CHAIN", "0")
    beat = _build_beat_schedule()
    assert "tdx-dayk-incremental-after-close" in beat
    assert "cn-history-csv-to-qlib-after-tdx" in beat
    assert "cn-history-mysql-to-qlib-after-tdx" not in beat
    assert beat["tdx-dayk-incremental-after-close"]["kwargs"] == {"dump_qlib_bin": False}


def test_build_beat_skips_duplicate_timescale_when_tdx_on(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("TIMESCALE_TDX_SYNC_BEAT", "1")
    monkeypatch.setenv("QLIB_CELERY_BEAT", "1")
    beat = _build_beat_schedule()
    assert "tdx-timescale-after-close" not in beat
    assert "qlib-mysql-incremental-sync" not in beat
    assert "qlib-tdx-incremental-nightly" in beat


def test_build_beat_timescale_when_tdx_off(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "0")
    monkeypatch.setenv("TIMESCALE_TDX_SYNC_BEAT", "1")
    beat = _build_beat_schedule()
    assert "tdx-timescale-after-close" in beat
