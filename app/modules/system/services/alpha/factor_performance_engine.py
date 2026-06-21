from __future__ import annotations

from typing import Any


class ConfigLoader:
    def __init__(self) -> None:
        self._config = {"factor_weights": {}}

    def get_config(self, key: str) -> Any:
        return self._config.get(key, {})


class FactorPerformanceEngine:
    def __init__(self) -> None:
        self.config_loader = ConfigLoader()

    def score_factor(self, factor_id: str) -> float:
        return self.config_loader.get_config("factor_weights").get(factor_id, 1.0)
