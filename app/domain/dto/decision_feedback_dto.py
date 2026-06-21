from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DecisionFeedbackDTO(BaseModel):
    schema_version: str = "v1"
    feedback_id: str
    decision_id: str
    user_id: int
    rating: str
    reasoning_path_id: str | None = None
    comment: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
