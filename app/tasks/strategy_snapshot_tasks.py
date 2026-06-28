from __future__ import annotations

"""Celery task: capture strategy deploy snapshot on pipeline deploy."""

from typing import Any

from app.core.logger import get_logger
from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService

logger = get_logger(__name__)


def run_capture_deploy_snapshot(
    *,
    strategy_name: str,
    label: str = "",
    notes: str = "",
    deployed_by: str = "celery",
    mark_active: bool = True,
) -> dict[str, Any]:
    """Sync helper for deploy hooks and Celery."""
    svc = StrategySnapshotService()
    snap = svc.capture_snapshot(
        strategy_name=strategy_name,
        label=label,
        notes=notes,
        deployed_by=deployed_by,
        mark_active=mark_active,
    )
    return {"ok": True, "snapshot_id": snap.id, "strategy_name": snap.strategy_name}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.strategy_snapshot_tasks.capture_deploy_snapshot")
    def capture_deploy_snapshot(
        strategy_name: str,
        label: str = "",
        notes: str = "",
        deployed_by: str = "celery",
        mark_active: bool = True,
    ) -> dict[str, Any]:
        try:
            return run_capture_deploy_snapshot(
                strategy_name=strategy_name,
                label=label,
                notes=notes,
                deployed_by=deployed_by,
                mark_active=mark_active,
            )
        except Exception as exc:
            logger.exception("capture_deploy_snapshot failed")
            return {"ok": False, "error": str(exc)}

else:
    capture_deploy_snapshot = None  # type: ignore[misc, assignment]
