from __future__ import annotations
"""Retail psychology guardian Celery beat — scan watchlist behavior and notify message center."""

from typing import Any

from app.modules.user.services.user.psychology_guardian_batch_service import (
    run_psychology_guardian_batch,
)
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool

logger = get_logger(__name__)


def run_retail_psychology_guardian_scan() -> dict[str, Any]:
    """Entry for Beat / manual trigger."""
    if not get_runtime_bool("ENABLE_RETAIL_PSYCHOLOGY_SCAN", True):
        return {
            "ok": True,
            "skipped": True,
            "reason": "ENABLE_RETAIL_PSYCHOLOGY_SCAN is disabled",
        }
    return run_psychology_guardian_batch(push_alerts=True)


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.retail_psychology_tasks.psychology_guardian_tick")
    def psychology_guardian_tick() -> dict[str, Any]:
        return run_retail_psychology_guardian_scan()

else:
    psychology_guardian_tick = None  # type: ignore[misc, assignment]
