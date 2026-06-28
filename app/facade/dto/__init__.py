"""Shim — re-exports from application-layer facade DTOs."""
from app.application.facade.dto import *  # noqa: F401, F403

import warnings
warnings.warn(
    "import from app.facade.dto is deprecated; use app.application.facade.dto instead",
    DeprecationWarning,
    stacklevel=2,
)