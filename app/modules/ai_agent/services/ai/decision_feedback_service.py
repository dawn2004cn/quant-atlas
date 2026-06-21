"""Collect decision feedback and forward signals to UserKnowledgeService."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.domain.decision_feedback import DecisionFeedback, FeedbackRating
from app.domain.dto.decision_feedback_dto import DecisionFeedbackDTO

logger = logging.getLogger(__name__)


class DecisionFeedbackService:
    """Persist feedback and propagate outcomes to user knowledge."""

    def __init__(
        self,
        *,
        store_path: Path | None = None,
        user_knowledge_service: Any | None = None,
        prompt_evolution_service: Any | None = None,
    ) -> None:
        self._path = Path(store_path or BASE_DIR / "instance" / "decision_feedback.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._knowledge = user_knowledge_service
        self._prompt = prompt_evolution_service
        self._lock = threading.Lock()

    def submit(
        self,
        *,
        user_id: int,
        decision_id: str,
        rating: str,
        reasoning_path_id: str | None = None,
        comment: str = "",
    ) -> DecisionFeedbackDTO:
        normalized = str(rating or "").strip().lower()
        if normalized not in {FeedbackRating.UP.value, FeedbackRating.DOWN.value}:
            raise ValueError("invalid_rating")
        fb = DecisionFeedback.new(
            decision_id=decision_id.strip(),
            user_id=int(user_id),
            rating=FeedbackRating(normalized),
            reasoning_path_id=(reasoning_path_id or "").strip() or None,
            comment=comment,
        )
        dto = DecisionFeedbackDTO(
            feedback_id=fb.feedback_id,
            decision_id=fb.decision_id,
            user_id=fb.user_id,
            rating=fb.rating.value,
            reasoning_path_id=fb.reasoning_path_id,
            comment=fb.comment,
            created_at=fb.created_at.isoformat().replace("+00:00", "Z"),
        )
        self._persist(dto)
        self._forward_to_knowledge(fb)
        self._forward_to_prompt(fb)
        return dto

    def _persist(self, dto: DecisionFeedbackDTO) -> None:
        with self._lock:
            rows = self._read_all()
            rows.append(dto.model_dump())
            rows = rows[-2000:]
            self._path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            logger.warning("DecisionFeedbackService._read_all: %s", exc)
            return []

    def _forward_to_knowledge(self, fb: DecisionFeedback) -> None:
        if self._knowledge is None:
            return
        outcome = "positive" if fb.rating == FeedbackRating.UP else "negative"
        try:
            self._knowledge.record_interaction(
                fb.user_id,
                outcome=outcome,
                evidence_refs=[fb.decision_id],
                action="decision_feedback",
                page="ai_decision",
            )
        except Exception as exc:
            logger.warning("DecisionFeedbackService knowledge forward: %s", exc)

    def _forward_to_prompt(self, fb: DecisionFeedback) -> None:
        if self._prompt is None:
            return
        try:
            score = 1.0 if fb.rating == FeedbackRating.UP else 0.0
            self._prompt.record_feedback(
                "decision_feedback",
                score,
                {
                    "decision_id": fb.decision_id,
                    "reasoning_path_id": fb.reasoning_path_id,
                    "comment": fb.comment,
                    "created_at": fb.created_at.isoformat().replace("+00:00", "Z"),
                },
            )
        except Exception as exc:
            logger.warning("DecisionFeedbackService prompt evolution forward: %s", exc)


_feedback_service: DecisionFeedbackService | None = None


def get_decision_feedback_service() -> DecisionFeedbackService:
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = DecisionFeedbackService()
    return _feedback_service


def configure_decision_feedback_service(svc: DecisionFeedbackService | None) -> None:
    global _feedback_service
    if svc is not None:
        _feedback_service = svc
