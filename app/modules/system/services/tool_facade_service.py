"""Backward-compat re-export for ``ToolFacadeService``."""
from __future__ import annotations

from app.modules.system.services.tools.tool_facade_service import (
    ToolFacadeService,
    get_tool_facade_service,
)

__all__ = [
    "ToolFacadeService",
    "get_tool_facade_service",
]
