from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.infrastructure.timeseries.sync_snapshot import (
    get_timeseries_sync_snapshot,
    record_timeseries_sync_snapshot,
)


def test_sync_snapshot_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.infrastructure.timeseries.sync_snapshot as mod

    monkeypatch.setattr(mod, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_SNAPSHOT_PATH", tmp_path / "timeseries_sync_snapshot.json")
    monkeypatch.setattr(mod, "_HISTORY_PATH", tmp_path / "timeseries_sync_history.jsonl")

    record_timeseries_sync_snapshot(
        {
            "ok": True,
            "mode": "incremental",
            "symbols_requested": 100,
            "questdb": {"rows_written": 4200},
            "clickhouse": {"rows_written": 0},
        },
        source="test",
    )
    snap = get_timeseries_sync_snapshot()
    assert snap is not None
    assert snap["source"] == "test"
    assert snap["ok"] is True
    assert snap["questdb_rows_written"] == 4200
    assert snap["recorded_at"]
    history = mod.get_timeseries_sync_history(limit=5)
    assert len(history) == 1
    assert history[0]["source"] == "test"


def test_sync_history_source_filter_and_trim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.infrastructure.timeseries.sync_snapshot as mod

    monkeypatch.setattr(mod, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_SNAPSHOT_PATH", tmp_path / "timeseries_sync_snapshot.json")
    monkeypatch.setattr(mod, "_HISTORY_PATH", tmp_path / "timeseries_sync_history.jsonl")
    monkeypatch.setattr(mod, "_HISTORY_MAX_LINES", 3)

    for i in range(5):
        record_timeseries_sync_snapshot(
            {"ok": True, "mode": "incremental", "questdb": {"rows_written": i}},
            source="celery_beat" if i % 2 == 0 else "sync",
        )

    all_runs = mod.get_timeseries_sync_history(limit=10)
    assert len(all_runs) == 3
    beat_runs = mod.get_timeseries_sync_history(limit=10, source="celery_beat")
    assert all(r["source"] == "celery_beat" for r in beat_runs)
    assert len(beat_runs) <= 3


def test_sync_progress_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.infrastructure.timeseries.sync_snapshot as mod

    monkeypatch.setattr(mod, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_PROGRESS_PATH", tmp_path / "timeseries_sync_progress.json")
    monkeypatch.setattr(mod, "_redis_client", lambda: None)

    mod.set_timeseries_sync_progress(status="running", symbols_total=100, symbols_done=40)
    prog = mod.get_timeseries_sync_progress()
    assert prog is not None
    assert prog["status"] == "running"
    assert prog["percent"] == 40
    mod.clear_timeseries_sync_progress()
    assert mod.get_timeseries_sync_progress() is None


def test_describe_questdb_sync_beat_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.infrastructure.timeseries.sync_snapshot import describe_questdb_sync_beat

    monkeypatch.setenv("QUESTDB_SYNC_BEAT", "1")
    beat = describe_questdb_sync_beat()
    assert beat["enabled"] is True
    assert beat["schedule_hour"] == 16
    assert beat["schedule_minute"] == 35
    assert "questdb_ohlcv_sync_tick" in beat["task"]


def test_describe_questdb_sync_beat_last_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.infrastructure.timeseries.sync_snapshot as mod
    from app.infrastructure.timeseries.sync_snapshot import describe_questdb_sync_beat

    monkeypatch.setenv("QUESTDB_SYNC_BEAT", "1")
    monkeypatch.setattr(mod, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_SNAPSHOT_PATH", tmp_path / "timeseries_sync_snapshot.json")
    monkeypatch.setattr(mod, "_PROGRESS_PATH", tmp_path / "timeseries_sync_progress.json")
    monkeypatch.setattr(mod, "_HISTORY_PATH", tmp_path / "timeseries_sync_history.jsonl")
    monkeypatch.setattr(mod, "_redis_client", lambda: None)

    record_timeseries_sync_snapshot(
        {
            "ok": True,
            "mode": "incremental",
            "symbols_requested": 10,
            "questdb": {"rows_written": 100},
            "clickhouse": {"rows_written": 0},
        },
        source="celery_beat",
    )
    record_timeseries_sync_snapshot(
        {"ok": False, "mode": "incremental", "questdb": {"rows_written": 0}},
        source="celery_beat",
    )
    beat = describe_questdb_sync_beat()
    assert beat["last_beat_run_at"]
    assert beat["last_beat_run_ok"] is False
    assert len(beat["recent_beat_runs"]) == 2

    mod.set_timeseries_sync_progress(status="running", symbols_total=50, symbols_done=25)
    beat2 = describe_questdb_sync_beat()
    assert beat2["sync_in_progress"] is True
    assert beat2["sync_progress"]["percent"] == 50


@patch("app.modules.data.services.tdx_code_cache.get_tdx_cn_universe")
@patch("app.infrastructure.timeseries.ohlcv_history_reader.probe_ohlcv_tables")
def test_describe_timeseries_backfill_status(mock_probe, mock_universe) -> None:
    from app.infrastructure.timeseries.sync_snapshot import describe_timeseries_backfill_status

    mock_probe.return_value = {"questdb_rows": 500_000, "questdb_sample_sh600519": 1200}
    mock_universe.return_value = ["sh600519", "sz000001"]
    out = describe_timeseries_backfill_status()
    assert out["target_rows"] == 1_000_000
    assert out["questdb_rows"] == 500_000
    assert out["coverage_pct"] == 50.0
    assert out["meets_target"] is False
    assert out["recommended"] is True
    assert out["universe_symbols"] == 2

