from __future__ import annotations

"""Hyper-Simulator request/response models (Quant Atlas 9.0 Step Three)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

HyperSimMode = Literal["backtest_mc", "price_path", "combined"]


class HyperSimRunRequest(BaseModel):
    """Unified Monte Carlo + backtest simulation request."""

    symbol: str
    market: str = "CN"
    strategy_name: str = "trend_following"
    mode: HyperSimMode = "combined"
    n_simulations: int = Field(default=1000, ge=100, le=20_000)
    horizon_days: int = Field(default=252, ge=20, le=1260)
    initial_capital: float = Field(default=100_000.0, gt=0)
    start: str = ""
    end: str = ""
    seed: int = 42
    scenario_id: str = ""
    inject_war_room: bool = False
    params: dict[str, Any] = Field(default_factory=dict)


class HyperSimEvidence(BaseModel):
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)


__all__ = ["HyperSimMode", "HyperSimRunRequest", "HyperSimEvidence"]
