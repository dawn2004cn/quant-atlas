"""Backward-compatible re-export for data optimizer routes."""

from app.modules.strategy.services.strategy.scenario_optimizer_service import (
    SCENARIO_CONFIGS,
    DataAccessScenario,
    DataScenarioOptimizer,
    ScenarioBasedDataService,
    ScenarioConfig,
)

__all__ = [
    "SCENARIO_CONFIGS",
    "DataAccessScenario",
    "DataScenarioOptimizer",
    "ScenarioBasedDataService",
    "ScenarioConfig",
]
