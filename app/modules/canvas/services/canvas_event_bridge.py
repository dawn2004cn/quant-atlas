"""Backward-compat re-export for CanvasEventBridge."""
from __future__ import annotations

from app.modules.system.services.canvas_event_bridge import *

__all__ = [
    "CanvasEventBridge",
    "get_canvas_event_bridge",
]
