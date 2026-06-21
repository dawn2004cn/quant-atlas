"""Backward-compat re-export for ``DecisionProvenanceService``."""
from __future__ import annotations

from app.modules.system.services.ui.decision_provenance_service import (
    DecisionProvenanceService,
)

__all__ = [
    "DecisionProvenanceService",
]
