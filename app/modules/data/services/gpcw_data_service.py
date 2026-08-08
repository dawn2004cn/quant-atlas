from __future__ import annotations
"""Backward-compatible alias for ``GpcwApplicationService``."""

from .gpcw_service import GpcwApplicationService, get_gpcw_service

GpcwDataService = GpcwApplicationService


def get_gpcw_data_service() -> GpcwApplicationService:
    """Get singleton GPCW service (alias of ``get_gpcw_service``)."""
    return get_gpcw_service()
