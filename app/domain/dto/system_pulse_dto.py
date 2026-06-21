from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SystemPulseComponentDTO(BaseModel):
    id: str
    label: str
    status: str
    detail: str = ""
    remedy: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class SystemPulseDTO(BaseModel):
    schema_version: str = "v1"
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    overall_status: str = "ok"
    components: list[SystemPulseComponentDTO] = Field(default_factory=list)

