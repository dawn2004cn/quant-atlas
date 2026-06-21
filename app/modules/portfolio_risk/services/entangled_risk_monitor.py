from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any


class EntangledRiskMonitor:
    def __init__(
        self,
        *,
        max_correlation: float = 0.7,
        joint_budget: float = 0.2,
        collapse_multiplier: float = 0.75,
    ) -> None:
        self.max_correlation = float(max_correlation)
        self.joint_budget = float(joint_budget)
        self.collapse_multiplier = float(collapse_multiplier)

    def analyze(self, positions: list[dict[str, Any]], total_value: float) -> dict[str, Any]:
        normalized = [self._normalize_position(pos, total_value) for pos in positions]
        normalized = [pos for pos in normalized if pos["weight"] > 0]
        pairs: list[dict[str, Any]] = []
        forced_reductions: list[dict[str, Any]] = []

        for left_index, left in enumerate(normalized):
            for right in normalized[left_index + 1 :]:
                correlation = self._semantic_correlation(left["vector"], right["vector"])
                if correlation < self.max_correlation:
                    continue
                joint_weight = left["weight"] + right["weight"]
                status = "locked" if joint_weight <= self.joint_budget else "collapsed"
                pair = {
                    "left": left["code"],
                    "right": right["code"],
                    "semantic_correlation": round(correlation, 4),
                    "joint_weight": round(joint_weight, 4),
                    "joint_budget": self.joint_budget,
                    "status": status,
                    "risk_action": "hold_joint_budget" if status == "locked" else "reduce_joint_exposure",
                }
                if status == "collapsed":
                    pair["required_joint_reduction"] = round(joint_weight - self.joint_budget, 4)
                    pair["reason"] = "semantic_entanglement_exceeds_joint_budget"
                    forced_reductions.extend(self._forced_reductions(left, right, joint_weight - self.joint_budget))
                pairs.append(pair)

        return {
            "enabled": True,
            "threshold": self.max_correlation,
            "joint_budget": self.joint_budget,
            "pairs": pairs,
            "forced_reductions": forced_reductions,
            "collapsed_pairs": len([item for item in pairs if item["status"] == "collapsed"]),
        }

    def _normalize_position(self, position: dict[str, Any], total_value: float) -> dict[str, Any]:
        value = float(position.get("value") or 0.0)
        weight = value / total_value if total_value > 0 else 0.0
        return {
            "code": str(position.get("code") or position.get("symbol") or "unknown"),
            "weight": weight,
            "vector": self._semantic_vector(position),
        }

    def _forced_reductions(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        excess_weight: float,
    ) -> list[dict[str, Any]]:
        total_weight = left["weight"] + right["weight"]
        if total_weight <= 0:
            return []
        left_reduction = excess_weight * (left["weight"] / total_weight)
        right_reduction = excess_weight * (right["weight"] / total_weight)
        return [
            {
                "code": left["code"],
                "reduce_weight": round(left_reduction, 4),
                "reason": "entangled_risk_collapse",
            },
            {
                "code": right["code"],
                "reduce_weight": round(right_reduction, 4),
                "reason": "entangled_risk_collapse",
            },
        ]

    def _semantic_vector(self, position: dict[str, Any]) -> dict[str, float]:
        tokens: list[str] = []
        for key in ("strategy_id", "strategy_logic", "logic_tags", "factors", "sector", "code", "symbol"):
            value = position.get(key)
            if isinstance(value, str):
                tokens.extend(self._tokenize(value))
            elif isinstance(value, list):
                for item in value:
                    tokens.extend(self._tokenize(str(item)))
        if not tokens:
            tokens.append("default")
        vector: dict[str, float] = {}
        for token in tokens:
            vector[token] = vector.get(token, 0.0) + 1.0
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {token: value / norm for token, value in vector.items()}

    def _semantic_correlation(self, left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(left.get(token, 0.0) * right.get(token, 0.0) for token in set(left) | set(right))
        left_norm = math.sqrt(sum(value * value for value in left.values())) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right.values())) or 1.0
        return max(0.0, min(1.0, dot / (left_norm * right_norm)))

    def _tokenize(self, value: str) -> list[str]:
        separators = " ,;:/\\|-_=()[]{}<>:"
        normalized = value.strip().lower()
        for separator in separators:
            normalized = normalized.replace(separator, " ")
        return [token for token in normalized.split() if len(token) > 1]


__all__ = ["EntangledRiskMonitor"]
