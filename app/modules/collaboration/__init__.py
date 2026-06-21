"""Collaboration bounded context — module wiring entrypoint."""

from __future__ import annotations

from typing import Any

from app.core.typed_registry import get_registry

__all__ = ["wire_module", "CollaborationContextModule"]

def wire_module(services: Any, session_factory: Any = None) -> None:
    """Wire collaboration services (ContextModule entrypoint)."""
    reg = get_registry()
    reg.wire_to(services)

# Re-export module metadata for discover_modules() after import.
from app.modules.collaboration.module import CollaborationContextModule  # noqa: E402
