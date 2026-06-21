"""Backward-compat re-export for ``QlibPipelineService`` and ``QlibIngestMeta``."""
from __future__ import annotations

from app.modules.data.services.qlib_pipeline_service import (
    QlibIngestMeta,
    QlibPipelineService,
)

__all__ = [
    "QlibIngestMeta",
    "QlibPipelineService",
]
