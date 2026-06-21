from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.domain.enums import MarketCode


class DataAccessScenario(str, Enum):
    MARKET_SCAN = "market_scan"
    SINGLE_STOCK_ANALYSIS = "single_stock_analysis"
    BACKTEST = "backtest"
    REALTIME_MONITOR = "realtime_monitor"
    HISTORICAL_RESEARCH = "historical_research"
    WRITER_RESULT = "writer_result"


@dataclass
class ScenarioConfig:
    scenario: DataAccessScenario
    description: str
    preload: bool = False
    cache: bool = False


SCENARIO_CONFIGS: dict[DataAccessScenario, ScenarioConfig] = {
    DataAccessScenario.MARKET_SCAN: ScenarioConfig(DataAccessScenario.MARKET_SCAN, "Full market scan with batch preload", True, True),
    DataAccessScenario.SINGLE_STOCK_ANALYSIS: ScenarioConfig(DataAccessScenario.SINGLE_STOCK_ANALYSIS, "Single stock analysis with caching", False, True),
    DataAccessScenario.BACKTEST: ScenarioConfig(DataAccessScenario.BACKTEST, "Backtest with preloaded data", True, True),
    DataAccessScenario.REALTIME_MONITOR: ScenarioConfig(DataAccessScenario.REALTIME_MONITOR, "Realtime monitoring", False, False),
    DataAccessScenario.HISTORICAL_RESEARCH: ScenarioConfig(DataAccessScenario.HISTORICAL_RESEARCH, "Historical research", True, True),
    DataAccessScenario.WRITER_RESULT: ScenarioConfig(DataAccessScenario.WRITER_RESULT, "Write operation", False, False),
}


class DataScenarioOptimizer:
    def __init__(self, tdx_adapter: Any | None = None) -> None:
        self.tdx_adapter = tdx_adapter
        self.scenarios = SCENARIO_CONFIGS

    def optimize(self, scenario: DataAccessScenario, symbols: list[str]) -> dict[str, Any]:
        return {
            "scenario": scenario.value,
            "symbols": list(symbols),
            "config": self.scenarios.get(scenario).__dict__ if self.scenarios.get(scenario) else None,
        }


class ScenarioBasedDataService:
    def __init__(self, *, tdx_adapter: Any | None = None, market_data_service: Any | None = None) -> None:
        self.tdx_adapter = tdx_adapter
        self.market_data_service = market_data_service
        self.optimizer = DataScenarioOptimizer(tdx_adapter)

    def scan_market(self, symbols: list[str]) -> dict[str, list[dict[str, Any]]]:
        if self.tdx_adapter is None:
            return {symbol: [] for symbol in symbols}
        results = {}
        for symbol in symbols:
            rows = self.tdx_adapter.get_stock_history(symbol, MarketCode.CN, "2020-01-01", "2026-12-31")
            results[symbol] = rows or []
        return results

    def run_backtest(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict[str, Any]]]:
        if self.tdx_adapter is None:
            return {symbol: [] for symbol in symbols}
        results = {}
        for symbol in symbols:
            rows = self.tdx_adapter.get_stock_history(symbol, MarketCode.CN, start, end)
            results[symbol] = rows or []
        return results

    def write_result(self, symbol: str, rows: list[dict[str, Any]]) -> bool:
        if self.market_data_service is not None and hasattr(self.market_data_service, "write_result"):
            return bool(self.market_data_service.write_result(symbol, rows))
        return isinstance(rows, list)


__all__ = [
    "DataAccessScenario",
    "DataScenarioOptimizer",
    "SCENARIO_CONFIGS",
    "ScenarioBasedDataService",
    "ScenarioConfig",
]
