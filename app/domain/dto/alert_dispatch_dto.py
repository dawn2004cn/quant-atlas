from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.dto.alert_dto import AlertLevel


class AlertDispatchChannelResultDTO(BaseModel):
    channel: str
    ok: bool
    skipped: bool = False
    reason: str = ""


class AlertDispatchResultDTO(BaseModel):
    """Outcome of pushing alert feed to external channels."""

    sent: int = 0
    failed: int = 0
    skipped: bool = False
    min_level: AlertLevel = "warning"
    alert_count: int = 0
    channels: list[AlertDispatchChannelResultDTO] = Field(default_factory=list)
    dispatched_at: datetime = Field(default_factory=datetime.now)
    deduplicated: bool = False
    fingerprint: str = ""
    message: str = ""
