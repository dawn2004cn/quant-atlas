from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HypothesisEvidenceItemDTO(BaseModel):
    text: str
    source: str = "indicator"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    trace_ref: dict[str, Any] | None = None


class HypothesisEvaluationDTO(BaseModel):
    hypothesis_id: str = "custom"
    user_hypothesis: str = ""
    verdict: str = "inconclusive"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_evidence: list[HypothesisEvidenceItemDTO] = Field(default_factory=list)
    contradicting_evidence: list[HypothesisEvidenceItemDTO] = Field(default_factory=list)
    summary: str = ""


class HypothesisCatalogItemDTO(BaseModel):
    id: str
    label: str
    description: str = ""


__all__ = [
    "HypothesisCatalogItemDTO",
    "HypothesisEvaluationDTO",
    "HypothesisEvidenceItemDTO",
]
