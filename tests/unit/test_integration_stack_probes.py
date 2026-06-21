"""Integration stack status probes (Sprint 25)."""

from __future__ import annotations

from app.config import get_settings
from app.modules.system.services.integration.integration_stack_service import (
    IntegrationStackService,
)


def test_stack_status_includes_execution_and_beat() -> None:
    svc = IntegrationStackService(settings=get_settings())
    status = svc.get_stack_status()
    layers = status.get("layers") or {}

    assert "execution_gateway" in layers
    exec_gw = layers["execution_gateway"]
    assert "qmt" in exec_gw
    assert exec_gw["qmt"].get("execution_mode") in (
        "disabled",
        "simulation",
        "live",
    )

    celery = layers.get("celery_tasks") or {}
    if celery.get("enabled"):
        beat = celery.get("questdb_beat") or {}
        assert "schedule_label" in beat
        assert beat.get("task", "").endswith("questdb_ohlcv_sync_tick")

    ts = layers.get("timeseries_ohlcv") or {}
    if ts.get("celery_beat"):
        assert "schedule_label" in ts["celery_beat"]
    assert "beat_history_count" in ts
    assert "recent_beat_runs" in ts
