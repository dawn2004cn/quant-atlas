"""Shim — re-exports from application-layer facade.

New code should import from app.application.facade directly.
"""
from app.application.facade import AIFacade, BacktestFacade, MarketFacade  # noqa: F401

import warnings
warnings.warn(
    "import from app.facade is deprecated; use app.application.facade instead",
    DeprecationWarning,
    stacklevel=2,
)
