"""Backward-compat re-export."""
from __future__ import annotations

from app.modules.strategy.services.market_regime.dummy_regime_service import *  # noqa: F401, F403

__all__ = [
    "DummyRegimeService",
]
