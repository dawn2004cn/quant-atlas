from __future__ import annotations
"""Celery: TDX lday → TimescaleDB only (split from TDX dayk MySQL/qlib pipeline)."""

from typing import Any

from app.modules.data.services.tdx_timescale_sync_service import run_tdx_timescale_sync
from app.core.logger import get_logger

logger = get_logger(__name__)


def run_scheduled_timescale_sync() -> dict[str, Any]:
    from app.core.runtime_config import get_runtime_int

    lim = get_runtime_int("TIMESCALE_SYNC_LIMIT", 0)
    return run_tdx_timescale_sync(
        mode="incremental",
        limit=None if lim <= 0 else lim,
    )


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.tdx_timescale_sync_tasks.tdx_timescale_sync_tick")
    def tdx_timescale_sync_tick() -> dict[str, Any]:
        return run_scheduled_timescale_sync()

else:
    tdx_timescale_sync_tick = None  # type: ignore[misc, assignment]
