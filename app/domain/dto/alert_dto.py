from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AlertLevel = Literal["info", "warning", "critical"]
AlertCategory = Literal["task", "factor", "data", "system", "execution", "consensus"]


class AlertEventDTO(BaseModel):
    """Unified alert item for the alert center feed."""

    id: str
    level: AlertLevel
    category: AlertCategory
    title: str
    message: str
    source: str
    occurred_at: str
    meta: dict[str, Any] = Field(default_factory=dict)


class AlertCenterFeedDTO(BaseModel):
    """Aggregated alert feed with summary counts."""

    items: list[AlertEventDTO] = Field(default_factory=list)
    total: int = 0
    counts_by_level: dict[str, int] = Field(default_factory=dict)
    counts_by_category: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)
