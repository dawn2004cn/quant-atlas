from __future__ import annotations

from abc import abstractmethod

from app.domain.decision_feedback import DecisionFeedback, FeedbackRating
from app.domain.dto.decision_context_dto import DecisionContextDTO


class DecisionProvenancePort:
    @abstractmethod
    def build_context(
        self,
        *,
        subject: str,
        input_snapshot: dict | None = None,
        model_version: str = "unknown",
        reasoning_trace: list[str] | None = None,
        evidence: list[dict] | None = None,
    ) -> DecisionContextDTO: ...


class DecisionFeedbackPort:
    @abstractmethod
    def submit(
        self,
        *,
        user_id: int,
        decision_id: str,
        rating: FeedbackRating | str,
        reasoning_path_id: str | None = None,
        comment: str = "",
    ) -> DecisionFeedback: ...
