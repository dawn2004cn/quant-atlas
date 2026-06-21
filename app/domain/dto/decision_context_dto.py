from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EvidenceNoteDTO(BaseModel):
    source: str
    title: str = ""
    confidence: float | None = None
    observed_at: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionContextDTO(BaseModel):
    schema_version: str = "v1"
    decision_id: str
    subject: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    model_version: str = "unknown"
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    reasoning_trace: list[str] = Field(default_factory=list)
    evidence: list[EvidenceNoteDTO] = Field(default_factory=list)

