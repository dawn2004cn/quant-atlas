"""Backward-compat re-export for ``DataSourceRouter`` and related data-routing types."""
from __future__ import annotations

from app.modules.data.services.data_router_service import (
    DataSourceConfig,
    DataSourceRouter,
    DataSourceType,
    DataQuery,
    MarketDataService,
    ReadWriteSplitDataService,
)

__all__ = [
    "DataSourceConfig",
    "DataSourceRouter",
    "DataSourceType",
    "DataQuery",
    "MarketDataService",
    "ReadWriteSplitDataService",
]
