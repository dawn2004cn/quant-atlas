"""Timeseries health probe infrastructure fields (Sprint 26)."""

from __future__ import annotations

from unittest.mock import patch


@patch("app.infrastructure.timeseries.ohlcv_history_reader.probe_ohlcv_tables")
@patch("app.infrastructure.timeseries.timeseries_factory.load_questdb_settings")
@patch("app.infrastructure.timeseries.timeseries_factory.load_clickhouse_settings")
def test_timeseries_health_includes_beat_and_execution(
    mock_ch_cfg,
    mock_q_cfg,
    mock_probe,
) -> None:
    from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

    mock_q_cfg.return_value = None
    mock_ch_cfg.return_value = None
    mock_probe.return_value = {"questdb_rows": 0}

    out = timeseries_health_probe()

    assert out["celery_beat"]["enabled"] is True
    assert "schedule_label" in out["celery_beat"]
    assert "qmt" in out["execution"]
