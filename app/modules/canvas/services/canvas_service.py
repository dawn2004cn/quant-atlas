"""Backward-compat re-export for CanvasService."""
from __future__ import annotations

from app.modules.system.services.canvas_service import *  # noqa: F401, F403

__all__ = [
    "CanvasGraph",
    "CanvasNode",
    "CanvasService",
]