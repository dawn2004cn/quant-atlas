"""Backward-compat re-export for ``GpcwDataService`` and GPCW service helpers."""
from __future__ import annotations

from app.modules.data.services.gpcw_data_service import (
    GpcwApplicationService,
    GpcwDataService,
    get_gpcw_data_service,
    get_gpcw_service,
)

__all__ = [
    "GpcwApplicationService",
    "GpcwDataService",
    "get_gpcw_data_service",
    "get_gpcw_service",
]
