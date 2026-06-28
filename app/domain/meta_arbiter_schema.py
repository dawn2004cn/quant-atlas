from __future__ import annotations

"""Cross-team meta-arbitration verdict models (Quant Atlas 8.0 P0)."""

from typing import Any

from pydantic import BaseModel, Field


class TeamSignalSummary(BaseModel):
    """Anonymized team-level arbiter signal."""

    team_fingerprint: str
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0)


class MetaArbiterVerdict(BaseModel):
    """Site-level synthesis when multiple team arbiters align."""

    ok: bool = True
    symbol: str
    market: str = "CN"
    meta_verdict: str
    meta_confidence: float = Field(ge=0.0, le=1.0)
    team_count: int = 0
    unanimous: bool = False
    dissent_teams: int = 0
    mode: str = "weighted_consensus"
    rationale: str = ""
    team_signals: list[TeamSignalSummary] = Field(default_factory=list)
    local_arbiter: dict[str, Any] | None = None
    activation_id: str = ""
    created_at: str = ""

    def to_alert_fields(self) -> dict[str, Any]:
        return {
            "meta_verdict": self.meta_verdict,
            "meta_confidence": round(self.meta_confidence, 3),
            "meta_unanimous": self.unanimous,
            "meta_rationale": self.rationale,
            "meta_activation_id": self.activation_id,
            "meta_mode": self.mode,
        }


__all__ = ["TeamSignalSummary", "MetaArbiterVerdict"]
