"""Backward-compat re-export for ``DecisionTraceService``."""
from __future__ import annotations

from app.modules.system.services.ui.decision_trace_service import (
    DecisionTraceService,
)

__all__ = [
    "DecisionTraceService",
]
