"""Shim — re-exports from application.facade.dto."""

from __future__ import annotations

import warnings

from app.application.facade.dto.ai_facade_dto import *  # noqa: F403

warnings.warn(
    "import from app.facade.dto is deprecated; use app.application.facade.dto instead",
    DeprecationWarning,
    stacklevel=2,
)
