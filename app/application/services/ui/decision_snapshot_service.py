"""Backward-compat re-export for ``DecisionSnapshotService``."""
from __future__ import annotations

from app.modules.system.services.ui.decision_snapshot_service import (
    DecisionSnapshotService,
)

__all__ = [
    "DecisionSnapshotService",
]
