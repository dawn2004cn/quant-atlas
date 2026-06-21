from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domain.dto.decision_context_dto import DecisionContextDTO, EvidenceNoteDTO


class DecisionProvenanceService:
    """Create a compact, replayable context for AI or strategy decisions."""

    def build_context(
        self,
        *,
        subject: str,
        input_snapshot: dict[str, Any] | None = None,
        model_version: str = "unknown",
        reasoning_trace: list[str] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> DecisionContextDTO:
        notes = [
            EvidenceNoteDTO(
                source=str(item.get("source") or "unknown"),
                title=str(item.get("title") or item.get("summary") or ""),
                confidence=item.get("confidence"),
                observed_at=item.get("observed_at") or item.get("timestamp"),
                payload=item,
            )
            for item in (evidence or [])
            if isinstance(item, dict)
        ]
        return DecisionContextDTO(
            decision_id=f"decision_{uuid4().hex[:12]}",
            subject=subject,
            model_version=model_version,
            input_snapshot=input_snapshot or {},
            reasoning_trace=reasoning_trace or [],
            evidence=notes,
        )

