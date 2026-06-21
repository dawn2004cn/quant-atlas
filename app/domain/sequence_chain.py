from __future__ import annotations
"""SequenceChain — causal provenance linking evidence, arbitration and trades."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_provenance_id() -> str:
    return f"prov-{uuid4().hex[:16]}"


def new_intent_id() -> str:
    return f"ci-{uuid4().hex[:12]}"


class SequenceStep(BaseModel):
    """One hop in a causal chain (event → evidence → decision → trade)."""

    step_id: str
    event_type: str
    label: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
    parent_step_id: str | None = None


class SequenceChain(BaseModel):
    """Full provenance chain for audit-grade decision replay."""

    provenance_id: str
    symbol: str
    market: str
    steps: list[SequenceStep] = Field(default_factory=list)
    root_event_type: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active | consensus | trade_linked | closed
    visibility: str = "private"  # private | team | public
    team_id: int | None = None
    owner_user_id: int | None = None

    def last_step_id(self) -> str | None:
        return self.steps[-1].step_id if self.steps else None


class CorrectionIntent(BaseModel):
    """Arbiter-driven parameter correction injected into TradePlanService."""

    intent_id: str
    provenance_id: str
    symbol: str
    market: str
    change_type: str  # regime_shift | stance_flip | risk_adjust
    prior_verdict: str = ""
    new_verdict: str = ""
    confidence: float = 0.0
    parameter_patch: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    applied: bool = False
