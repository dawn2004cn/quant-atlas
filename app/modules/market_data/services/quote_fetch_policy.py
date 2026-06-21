"""Feature flags for market quote fetch strategy (T-5)."""

from __future__ import annotations

import os


def async_market_quotes_enabled() -> bool:
    """When true, missing CN quotes use ``get_quotes_async`` via ``run_async``."""
    return os.getenv("ENABLE_ASYNC_MARKET_QUOTES", "").lower() in ("1", "true", "yes")
