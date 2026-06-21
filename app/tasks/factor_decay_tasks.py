from __future__ import annotations

"""Celery task: persist factor decay events to MySQL."""

import asyncio
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_log_factor_decay_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync runner for FactorRepository.log_decay_event (async repo)."""
    try:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_factor_repository

        settings = get_settings()
        if not settings.use_mysql:
            return {"ok": False, "skipped": True, "reason": "mysql_not_enabled"}

        repo = create_factor_repository(settings)
        if not hasattr(repo, "log_decay_event"):
            return {"ok": False, "skipped": True, "reason": "log_decay_event_unavailable"}

        async def _run() -> int:
            return await repo.log_decay_event(**payload)

        log_id = asyncio.run(_run())
        return {"ok": True, "log_id": log_id}
    except Exception as exc:
        logger.warning("log_factor_decay_event failed: %s", exc)
        return {"ok": False, "error": str(exc)}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(bind=True, name="factor.log_decay_event")
    def log_factor_decay_event_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return run_log_factor_decay_event(payload)

else:
    log_factor_decay_event_task = None  # type: ignore[misc, assignment]


__all__ = ["log_factor_decay_event_task", "run_log_factor_decay_event"]
