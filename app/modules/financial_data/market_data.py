"""Backward-compat re-export."""
from __future__ import annotations

from app.modules.data.services.financial_market_data import *  # noqa: F401, F403

__all__ = [
    "fetch_market_data",
    "check_external_connection",
]
