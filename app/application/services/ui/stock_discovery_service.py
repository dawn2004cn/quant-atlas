"""Backward-compat re-export for ``StockDiscoveryService`` and ``DiscoveryTag``."""
from __future__ import annotations

from app.modules.system.services.ui.stock_discovery_service import (
    DiscoveryTag,
    StockDiscoveryService,
)

__all__ = [
    "DiscoveryTag",
    "StockDiscoveryService",
]
