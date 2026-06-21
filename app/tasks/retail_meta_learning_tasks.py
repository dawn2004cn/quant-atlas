from __future__ import annotations
"""Retail meta-learning Celery beat — evolve prompts from AutoValidator failures."""

from typing import Any

from app.modules.user.services.user.meta_learning_evolve_service import run_meta_learning_evolve
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool

logger = get_logger(__name__)


def run_retail_meta_learning_evolve() -> dict[str, Any]:
    """Entry for Beat / manual trigger."""
    return run_meta_learning_evolve(force=False)


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.retail_meta_learning_tasks.meta_learning_evolve_tick")
    def meta_learning_evolve_tick() -> dict[str, Any]:
        return run_retail_meta_learning_evolve()

else:
    meta_learning_evolve_tick = None  # type: ignore[misc, assignment]
