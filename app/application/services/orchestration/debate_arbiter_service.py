"""Backward-compat re-export for ``DebateArbiterService``."""
from __future__ import annotations

from app.modules.system.services.debate_arbiter_service import (
    DebateArbiterService,
)

__all__ = [
    "DebateArbiterService",
]
