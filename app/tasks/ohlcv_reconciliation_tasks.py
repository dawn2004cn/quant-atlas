from __future__ import annotations
"""Celery: TDX vs timeseries store freshness spot-check."""

from typing import Any

from app.modules.data.services.ohlcv_reconciliation_service import run_ohlcv_reconciliation
from app.core.logger import get_logger

logger = get_logger(__name__)


def run_scheduled_ohlcv_reconciliation() -> dict[str, Any]:
    return run_ohlcv_reconciliation()


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.ohlcv_reconciliation_tasks.ohlcv_reconciliation_tick")
    def ohlcv_reconciliation_tick() -> dict[str, Any]:
        return run_scheduled_ohlcv_reconciliation()

else:
    ohlcv_reconciliation_tick = None  # type: ignore[misc, assignment]
