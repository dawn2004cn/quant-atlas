"""Shim — re-exports from application-layer facade."""

from __future__ import annotations

import warnings

from app.application.facade.ai_facade import AIFacade, sanitize_user_prompt

warnings.warn(
    "import from app.facade is deprecated; use app.application.facade instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AIFacade", "sanitize_user_prompt"]
