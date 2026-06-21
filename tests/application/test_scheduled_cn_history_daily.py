"""收盘 A 股历史日更 Celery 任务编排."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

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
        dump_qlib_bin=False,
        dump_max_workers=8,
    )


def test_scheduled_cn_history_daily_runs_bin_after_tdx_ok() -> None:
    svc = MagicMock()
    svc.incremental_sync_from_tdx_dayk.return_value = {"ok": True, "stats": {"codes_ok": 1}}
    with patch(
        "app.tasks.data_backfill_tasks.create_tdx_dayk_sync_service",
        return_value=svc,
    ), patch(
        "app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync",
        return_value={"ok": True, "synced_stocks": 1},
    ) as mock_bin:
        out = data_backfill_tasks.scheduled_cn_history_daily()
    assert out["ok"] is True
    assert out["stage"] == "done"
    mock_bin.assert_called_once()


def test_build_beat_includes_tdx_dayk_when_flag_on(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("QLIB_CELERY_BEAT", "0")
    monkeypatch.setenv("TDX_USE_SCHEDULED_DAILY_CHAIN", "1")
    beat = _build_beat_schedule()
    assert "cn-history-daily-after-close" in beat
    assert beat["cn-history-daily-after-close"]["task"].endswith("scheduled_cn_history_daily")


def test_build_beat_legacy_split_when_daily_chain_off(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("TDX_USE_SCHEDULED_DAILY_CHAIN", "0")
    beat = _build_beat_schedule()
    assert "tdx-dayk-incremental-after-close" in beat
    assert "cn-history-mysql-to-qlib-after-tdx" in beat
    assert beat["tdx-dayk-incremental-after-close"]["kwargs"] == {"dump_qlib_bin": False}


def test_build_beat_skips_duplicate_mysql_when_tdx_on(monkeypatch) -> None:
    from app.celery_app import _build_beat_schedule

    monkeypatch.setenv("TDX_DAYK_CELERY_BEAT", "1")
    monkeypatch.setenv("QLIB_CELERY_BEAT", "1")
    beat = _build_beat_schedule()
    assert "qlib-mysql-incremental-sync" not in beat
    assert "qlib-tdx-incremental-nightly" in beat
