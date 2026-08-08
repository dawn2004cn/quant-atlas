"""Celery / sync entry for offline RL research training."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.modules.strategy.services.rl_research_service import run_rl_research_tick

logger = get_logger(__name__)


def run_rl_research_job(**kwargs: Any) -> dict[str, Any]:
    return run_rl_research_tick(**kwargs)


try:
    from app.celery_app import celery

    @celery.task(name="app.tasks.rl_research_tasks.rl_research_tick")
    def rl_research_tick(**kwargs: Any) -> dict[str, Any]:
        return run_rl_research_job(**kwargs)

except Exception:  # pragma: no cover - celery optional at import
    logger.debug("rl_research celery task not registered", exc_info=True)
