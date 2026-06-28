from __future__ import annotations
"""War Room virtual scenario descriptors (Quant Atlas 7.0 Step Three)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SimulationScenarioType(str, Enum):
    RATE_HIKE = "rate_hike"
    MARKET_SHOCK = "market_shock"
    SECTOR_BLACK_SWAN = "sector_black_swan"
    VOLATILITY_SPIKE = "volatility_spike"
    CUSTOM_HYPOTHESIS = "custom_hypothesis"


class WarRoomPosition(BaseModel):
    """Portfolio leg for counterfactual stress."""

    symbol: str
    shares: float = Field(default=0.0, ge=0)
    current_value: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, ge=0)
    sector: str | None = None
    beta: float = Field(default=1.0, ge=0)

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        return (value or "").strip().lower()


class SimulationScenario(BaseModel):
    """Virtual macro / market event injected into War Room."""

    scenario_type: SimulationScenarioType
    rate_hike_bps: int | None = Field(default=None, ge=0, le=500)
    market_shock_pct: float | None = None
    sector: str | None = None
    sector_shock_pct: float | None = Field(default=-20.0)
    contagion_pct: float | None = Field(default=-2.0)
    volatility_multiplier: float | None = Field(default=1.5, ge=1.0)
    hypothesis_text: str | None = None
    label: str | None = None

    @classmethod
    def from_preset(cls, preset: dict[str, Any]) -> SimulationScenario:
        """Build scenario from War Room preset dict."""
        st = preset.get("scenario_type") or SimulationScenarioType.CUSTOM_HYPOTHESIS.value
        return cls(
            scenario_type=SimulationScenarioType(st),
            rate_hike_bps=preset.get("rate_hike_bps"),
            market_shock_pct=preset.get("market_shock_pct"),
            sector=preset.get("sector"),
            sector_shock_pct=preset.get("sector_shock_pct"),
            contagion_pct=preset.get("contagion_pct"),
            volatility_multiplier=preset.get("volatility_multiplier"),
            hypothesis_text=preset.get("hypothesis_text"),
            label=preset.get("label"),
        )

    def display_label(self) -> str:
        if self.label:
            return self.label
        if self.scenario_type == SimulationScenarioType.RATE_HIKE:
            bps = self.rate_hike_bps or 25
            return f"加息 {bps}bp"
        if self.scenario_type == SimulationScenarioType.MARKET_SHOCK:
            pct = self.market_shock_pct or 0.0
            return f"全市场冲击 {pct:+.1f}%"
        if self.scenario_type == SimulationScenarioType.SECTOR_BLACK_SWAN:
            sec = self.sector or "目标板块"
            pct = self.sector_shock_pct or -20.0
            return f"{sec} 黑天鹅 {pct:+.1f}%"
        if self.scenario_type == SimulationScenarioType.VOLATILITY_SPIKE:
            mult = self.volatility_multiplier or 1.5
            return f"波动率飙升 ×{mult:.1f}"
        if self.scenario_type == SimulationScenarioType.CUSTOM_HYPOTHESIS:
            return (self.hypothesis_text or "自定义假设")[:48]
        return self.scenario_type.value


class WarRoomRunRequest(BaseModel):
    """API payload for a single War Room stress run."""

    scenario: SimulationScenario
    positions: list[WarRoomPosition] = Field(default_factory=list)
    cash: float = Field(default=0.0, ge=0)
    use_watchlist_fallback: bool = True
    run_arbiter: bool = True
    arbiter_top_n: int = Field(default=3, ge=0, le=10)
    inject_virtual_events: bool = True

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> WarRoomRunRequest:
        scenario_raw = body.get("scenario") or body
        if "scenario_type" in body and "scenario" not in body:
            scenario_raw = body
        return cls.model_validate(
            {
                "scenario": scenario_raw,
                "positions": body.get("positions") or [],
                "cash": body.get("cash", 0.0),
                "use_watchlist_fallback": body.get("use_watchlist_fallback", True),
                "run_arbiter": body.get("run_arbiter", True),
                "arbiter_top_n": body.get("arbiter_top_n", 3),
                "inject_virtual_events": body.get("inject_virtual_events", True),
            }
        )


__all__ = [
    "SimulationScenarioType",
    "WarRoomPosition",
    "SimulationScenario",
    "WarRoomRunRequest",
]
