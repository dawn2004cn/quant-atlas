"""Process-wide settings singleton (single load from environment).

.. deprecated::
    This module delegates to ``app.config.settings.get_settings()`` which
    now uses Pydantic Settings. The module is retained for backward-compat.
"""

from __future__ import annotations

from app.config.settings import get_settings as _get_settings
from app.config.settings import reset_settings as _reset_settings


def get_settings():
    """Return cached AppSettings; loads from env once per process."""
    return _get_settings()


def reset_settings() -> None:
    """Clear cache (tests only)."""
    _reset_settings()
