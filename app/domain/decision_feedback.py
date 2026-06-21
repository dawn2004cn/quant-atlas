"""Decision feedback entity — user thumbs-up/down on AI reasoning paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class FeedbackRating(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True)
class DecisionFeedback:
    """User feedback on a specific AI decision or reasoning path."""

    feedback_id: str
    decision_id: str
    user_id: int
    rating: FeedbackRating
    reasoning_path_id: str | None = None
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def new(
        *,
        decision_id: str,
        user_id: int,
        rating: FeedbackRating,
        reasoning_path_id: str | None = None,
        comment: str = "",
    ) -> DecisionFeedback:
        return DecisionFeedback(
            feedback_id=f"fb_{uuid4().hex[:12]}",
            decision_id=decision_id,
            user_id=user_id,
            rating=rating,
            reasoning_path_id=reasoning_path_id,
            comment=(comment or "").strip()[:500],
        )
