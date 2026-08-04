"""Deprecated shim — use ``app.application.facade`` instead."""

from __future__ import annotations

import warnings

from app.application.facade.market_data_facade import MarketDataFacade

warnings.warn(
    "app.application.facades is deprecated; use app.application.facade instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MarketDataFacade"]
