from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionResearchSnapshotDTO(BaseModel):
    """Frozen decision brief + market quote for collaboration / replay."""

    snapshot_schema_version: str = "v1"
    id: str
    symbol: str
    market: str = "CN"
    label: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "anonymous"
    decision_brief: dict[str, Any] = Field(default_factory=dict)
    quote_snapshot: dict[str, Any] = Field(default_factory=dict)
    sector_context: dict[str, Any] = Field(default_factory=dict)
    share_path: str = ""
    share_token: str = ""
    share_public_path: str = ""
    share_expires_at: datetime | None = None
    notes: str = ""
