"""Backward-compat re-export for ``build_research_pipeline_snapshot``."""
from __future__ import annotations

from app.modules.data.services.research_pipeline_snapshot import (
    build_research_pipeline_snapshot,
)

__all__ = [
    "build_research_pipeline_snapshot",
]
