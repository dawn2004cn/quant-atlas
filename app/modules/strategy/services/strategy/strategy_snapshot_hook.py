from __future__ import annotations

"""Hooks to capture strategy snapshots on deploy events."""

import logging
from typing import Any

from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.core.runtime_config import get_runtime_bool

logger = logging.getLogger(__name__)


def capture_on_deploy(
    *,
    strategy_name: str,
    label: str = "",
    notes: str = "",
    deployed_by: str = "deploy_hook",
    strategy_config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Capture snapshot when ``STRATEGY_SNAPSHOT_ON_DEPLOY`` is enabled (default on)."""
    if not get_runtime_bool("STRATEGY_SNAPSHOT_ON_DEPLOY", True):
        return None
    try:
        svc = StrategySnapshotService()
        snap = svc.capture_snapshot(
            strategy_name=strategy_name,
            label=label,
            notes=notes,
            strategy_config=strategy_config or {},
            deployed_by=deployed_by,
            mark_active=True,
        )
        return {"snapshot_id": snap.id, "strategy_name": snap.strategy_name, "label": snap.label}
    except Exception as exc:
        logger.warning("capture_on_deploy failed: %s", exc)
        return None
