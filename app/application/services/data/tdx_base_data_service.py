"""Backward-compat re-export for ``TdxBaseDataService`` and related types."""
from __future__ import annotations

from app.modules.data.services.tdx_base_data_service import (
    ConflictStrategy,
    SyncMode,
    TdxBaseDataService,
    TdxBaseIngestResult,
)

__all__ = [
    "ConflictStrategy",
    "SyncMode",
    "TdxBaseDataService",
    "TdxBaseIngestResult",
]
