"""Backward-compat re-export for ``TdxDaykSyncService`` and ``SyncResult``."""
from __future__ import annotations

from app.modules.data.services.tdx_dayk_sync_service import (
    SyncResult,
    TdxDaykSyncService,
)

__all__ = [
    "SyncResult",
    "TdxDaykSyncService",
]
