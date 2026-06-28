from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategySpec:
    """Minimal strategy specification shared by Phase 16/17 modules."""

    strategy_id: str = "manual"
    name: str = "Manual Strategy"
    entry_conditions: list[dict[str, Any]] = field(default_factory=list)
    exit_rules: list[dict[str, Any]] = field(default_factory=list)
    risk: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    capital_per_trade: float = 0.1
    children: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_canvas(cls, canvas_json: dict[str, Any]) -> StrategySpec:
        spec = canvas_json.get("spec", {}) if isinstance(canvas_json, dict) else {}
        return cls(
            strategy_id=str(canvas_json.get("strategy_id") or spec.get("strategy_id") or canvas_json.get("name") or "canvas_strategy"),
            name=str(canvas_json.get("name") or spec.get("name") or "Canvas Strategy"),
            entry_conditions=spec.get("entry_conditions") or spec.get("children") or [],
            exit_rules=spec.get("exit_rules", []),
            risk=spec.get("risk", {}),
            metrics=spec.get("metrics", {}),
            capital_per_trade=float(spec.get("capital_per_trade", 0.1)),
            children=spec.get("children", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "entry_conditions": self.entry_conditions,
            "children": self.children,
            "exit_rules": self.exit_rules,
            "risk": self.risk,
            "metrics": self.metrics,
            "capital_per_trade": self.capital_per_trade,
        }
