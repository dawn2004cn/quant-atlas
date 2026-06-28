from __future__ import annotations
"""Data Truth Guardian schemas (Quant Atlas 9.0 Step Four)."""

from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field

HealActionType = Literal["acknowledge", "resync_qlib", "rescan", "clear_pending"]


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    EXTREME = "extreme"


class GuardianScanRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    market: str = "CN"
    auto_heal: bool = False


class DataHealAction(BaseModel):
    action: HealActionType
    symbol: str
    market: str = "CN"
    reason: str = ""
    dispatched: bool = False
    task_name: str = ""
    evidence: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class GuardianQuorumRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    market: str = "CN"


class GuardianManifest(BaseModel):
    enabled: bool = True
    diff_threshold_pct: float = 0.5
    sources: list[str] = Field(default_factory=lambda: ["TDX", "Qlib", "AkShare"])
    heal_actions: list[str] = Field(default_factory=list)
    mesh_linked: bool = False
    quorum_enabled: bool = True


__all__ = [
    "GuardianScanRequest",
    "GuardianQuorumRequest",
    "DataHealAction",
    "GuardianManifest",
    "MarketRegime",
    "HealActionType",
]
