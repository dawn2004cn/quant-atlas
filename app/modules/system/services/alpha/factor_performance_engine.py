from __future__ import annotations

from typing import Any

from app.domain.quant.factor_diagnostics import diagnose_factor


class ConfigLoader:
    def __init__(self) -> None:
        self._config = {"factor_weights": {}}

    def get_config(self, key: str) -> Any:
        return self._config.get(key, {})


class FactorPerformanceEngine:
    def __init__(self) -> None:
        self.config_loader = ConfigLoader()
        self._observations: dict[str, tuple[list[float], list[float]]] = {}

    def record(self, factor_id: str, factor_values: list[Any], forward_returns: list[Any]) -> dict[str, Any]:
        self._observations[factor_id] = ([float(x) for x in factor_values], [float(x) for x in forward_returns])
        score = self.score_factor(factor_id)
        weights = self.config_loader.get_config("factor_weights")
        if not isinstance(weights, dict):
            weights = {}
            self.config_loader._config["factor_weights"] = weights
        weights[factor_id] = score
        return self.diagnose(factor_id) or {}

    def diagnose(self, factor_id: str) -> dict[str, Any] | None:
        obs = self._observations.get(factor_id)
        if not obs:
            return None
        return diagnose_factor(obs[0], obs[1])

    def score_factor(self, factor_id: str) -> float:
        if factor_id in self._observations:
            diag = diagnose_factor(*self._observations[factor_id])
            return 1.0 + abs(float(diag.get("rank_ic") or 0.0))
        weights = self.config_loader.get_config("factor_weights")
        if not isinstance(weights, dict):
            return 1.0
        return float(weights.get(factor_id, 1.0))
