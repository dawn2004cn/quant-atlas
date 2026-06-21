"""Backward-compat re-export for ``UserApplicationService``."""
from __future__ import annotations

from app.modules.user.services.user.user_service import (
    UserApplicationService,
)

__all__ = [
    "UserApplicationService",
]
