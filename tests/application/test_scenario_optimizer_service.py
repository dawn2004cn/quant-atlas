"""Scenario optimizer MySQL fallback and quote routing."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.strategy.services.strategy.scenario_optimizer_service import (
    DataAccessScenario,
    DataScenarioOptimizer,
    ScenarioBasedDataService,
)
from app.domain.enums import MarketCode


class _EmptyTdx:
    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        return []

    def preload_symbols(self, symbols: list[str], market: MarketCode) -> int:
        return 0


class _FakeDaykRepo:
    def fetch_history_rows(self, table: str, codes: list[str]) -> list[dict]:
        return [
            {
                "stock_code": "sh600519",
                "date": "2026-01-15",
                "open": 2,
                "high": 3,
                "low": 2,
                "close": 3,
                "volume": 200,
                "amount": 2000,
            }
        ]


def test_historical_research_falls_back_to_mysql_when_tdx_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.data.services.data_router_service.get_tdx_dayk_write_port",
        lambda: _FakeDaykRepo(),
    )
    optimizer = DataScenarioOptimizer(_EmptyTdx())
    rows = optimizer.get_data_for_scenario(
        DataAccessScenario.HISTORICAL_RESEARCH,
        "600519",
        MarketCode.CN,
        "2026-01-10",
        "2026-01-20",
    )
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-15"


def test_monitor_realtime_delegates_to_market_data_service(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"code": "600519", "price": 1688.0}

    class _FakeMarketDataService:
        def get_realtime_quote(self, symbol: str, market: MarketCode) -> dict[str, Any] | None:
            assert symbol == "600519"
            assert market == MarketCode.CN
            return expected

    svc = ScenarioBasedDataService(_EmptyTdx(), market_data_service=_FakeMarketDataService())
    out = svc.monitor_realtime(["600519"])
    assert out["600519"] == expected


def test_scenario_optimizer_reexport_shim() -> None:
    from app.application.services import scenario_optimizer_service as shim

    assert shim.ScenarioBasedDataService is ScenarioBasedDataService
    assert shim.DataAccessScenario is DataAccessScenario
