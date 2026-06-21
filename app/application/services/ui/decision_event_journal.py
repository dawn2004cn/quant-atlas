"""Backward-compat re-export for ``DecisionEventJournal``."""
from __future__ import annotations

from app.modules.system.services.ui.decision_event_journal import (
    DecisionEventJournal,
)

__all__ = [
    "DecisionEventJournal",
]
