"""AI facade request/response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIAnalysisRequestDTO(BaseModel):
    """Validated AI analysis request."""

    symbol: str = Field(..., min_length=1, max_length=32)
    market: str = Field(default="CN", min_length=2, max_length=8)
    analysis_type: str = Field(default="standard", pattern=r"^(standard|deep)$")
    user_hypothesis: str | None = None
    hypothesis_id: str | None = None
    evidence_depth: str = Field(default="standard", pattern=r"^(standard|deep)$")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        return symbol


class AIAnalysisResultDTO(BaseModel):
    """Normalized AI analysis output for API consumers."""

    model_config = ConfigDict(extra="allow")

    symbol: str | None = None
    market: str | None = None
    conclusion: str | None = None
    confidence: float | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    prompt_trace: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_service(cls, payload: Any) -> AIAnalysisResultDTO:
        if hasattr(payload, "model_dump"):
            data: dict[str, Any] = payload.model_dump()
        elif isinstance(payload, dict):
            data = dict(payload)
        else:
            data = {"result": payload}

        ai_block = data.get("ai") if isinstance(data.get("ai"), dict) else {}
        hypothesis = data.get("hypothesis_evaluation") if isinstance(
            data.get("hypothesis_evaluation"), dict
        ) else {}
        decision = data.get("decision") if isinstance(data.get("decision"), dict) else {}

        conclusion = (
            ai_block.get("summary")
            or ai_block.get("conclusion")
            or ai_block.get("recommendation")
            or hypothesis.get("summary")
        )
        confidence = hypothesis.get("confidence")
        if confidence is None:
            confidence = ai_block.get("confidence")

        evidence: list[dict[str, Any]] = []
        for key in ("evidence", "evidence_notes", "notes"):
            block = decision.get(key) or ai_block.get(key)
            if isinstance(block, list):
                evidence = [item if isinstance(item, dict) else {"text": str(item)} for item in block]
                break

        risk_flags: list[str] = []
        raw_flags = ai_block.get("risk_flags") or decision.get("risk_flags") or []
        if isinstance(raw_flags, list):
            risk_flags = [str(item) for item in raw_flags]

        prompt_trace = {}
        for key in ("prompt_hash", "prompt_version", "prompt_id", "trace"):
            if ai_block.get(key) is not None:
                prompt_trace[key] = ai_block[key]
        if data.get("prompt_trace") and isinstance(data["prompt_trace"], dict):
            prompt_trace.update(data["prompt_trace"])

        return cls.model_validate(
            {
                "symbol": data.get("symbol"),
                "market": data.get("market"),
                "conclusion": conclusion,
                "confidence": confidence,
                "evidence": evidence,
                "risk_flags": risk_flags,
                "prompt_trace": prompt_trace,
                "decision_id": data.get("decision_id"),
                "raw": data,
            }
        )
