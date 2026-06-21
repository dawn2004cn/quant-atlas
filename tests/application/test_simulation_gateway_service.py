from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.execution.services.simulation_gateway_service import SimulationGatewayService
from app.domain.simulation_scenario import (
    SimulationScenario,
    SimulationScenarioType,
    WarRoomPosition,
    WarRoomRunRequest,
)


@pytest.fixture
def gateway(tmp_path: Path) -> SimulationGatewayService:
    store = tmp_path / "runs.jsonl"
    return SimulationGatewayService(
        portfolio_service=None,
        watchlist_service=None,
        swarm_arbiter_service=None,
        store_path=store,
    )


def test_list_scenarios_has_presets(gateway: SimulationGatewayService) -> None:
    out = gateway.list_scenarios()
    assert out["ok"] is True
    assert len(out["presets"]) >= 4
    ids = {p["id"] for p in out["presets"]}
    assert "rate_hike_50bp" in ids
    assert "market_crash_8pct" in ids


def test_market_shock_revalues_portfolio(gateway: SimulationGatewayService) -> None:
    req = WarRoomRunRequest(
        scenario=SimulationScenario(
            scenario_type=SimulationScenarioType.MARKET_SHOCK,
            market_shock_pct=-10.0,
        ),
        positions=[
            WarRoomPosition(symbol="sz000001", current_value=100_000.0, beta=1.0),
            WarRoomPosition(symbol="sz000002", current_value=50_000.0, beta=0.5),
        ],
        cash=50_000.0,
        use_watchlist_fallback=False,
        run_arbiter=False,
        inject_virtual_events=False,
    )
    out = gateway.run_war_room(user_id=42, request=req)
    assert out["ok"] is True
    portfolio = out["portfolio"]
    assert portfolio["base_total"] == 200_000.0
    assert portfolio["delta_pct"] < 0
    assert out["risk_grade"] in {"watch", "elevated", "high", "critical"}
    assert len(out["positions"]) == 2
    assert out["positions"][0]["shock_pct"] == pytest.approx(-10.0)
    assert out["positions"][1]["shock_pct"] == pytest.approx(-5.0)


def test_sector_black_swan_hits_matching_sector(gateway: SimulationGatewayService) -> None:
    req = WarRoomRunRequest(
        scenario=SimulationScenario(
            scenario_type=SimulationScenarioType.SECTOR_BLACK_SWAN,
            sector="科技",
            sector_shock_pct=-20.0,
            contagion_pct=-2.0,
        ),
        positions=[
            WarRoomPosition(symbol="sz300001", current_value=80_000.0, sector="科技", beta=1.0),
            WarRoomPosition(symbol="sz000001", current_value=20_000.0, sector="银行", beta=1.0),
        ],
        use_watchlist_fallback=False,
        run_arbiter=False,
        inject_virtual_events=False,
    )
    out = gateway.run_war_room(user_id=1, request=req)
    tech = next(p for p in out["positions"] if p["symbol"] == "sz300001")
    bank = next(p for p in out["positions"] if p["symbol"] == "sz000001")
    assert tech["shock_pct"] == pytest.approx(-20.0)
    assert bank["shock_pct"] == pytest.approx(-2.0)


def test_watchlist_fallback_and_persist(gateway: SimulationGatewayService, tmp_path: Path) -> None:
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = ["sz000001", "sz000002"]
    gw = SimulationGatewayService(
        watchlist_service=watchlist,
        store_path=tmp_path / "runs.jsonl",
    )
    req = WarRoomRunRequest(
        scenario=SimulationScenario(
            scenario_type=SimulationScenarioType.RATE_HIKE,
            rate_hike_bps=50,
        ),
        use_watchlist_fallback=True,
        run_arbiter=False,
        inject_virtual_events=False,
    )
    out = gw.run_war_room(user_id=7, request=req)
    assert out["ok"] is True
    watchlist.list_symbols.assert_called_once_with(7)
    recent = gw.list_recent_runs(7, limit=5)
    assert recent["count"] == 1
    assert recent["runs"][0]["scenario_type"] == "rate_hike"


def test_virtual_event_injection(gateway: SimulationGatewayService) -> None:
    from app.agents.research.debate_bus import clear_debate_buffer, get_recent_debate_rounds

    clear_debate_buffer()
    req = WarRoomRunRequest(
        scenario=SimulationScenario(
            scenario_type=SimulationScenarioType.MARKET_SHOCK,
            market_shock_pct=-8.0,
        ),
        positions=[WarRoomPosition(symbol="sz000001", current_value=100_000.0)],
        use_watchlist_fallback=False,
        run_arbiter=False,
        inject_virtual_events=True,
    )
    out = gateway.run_war_room(user_id=1, request=req)
    assert out["virtual_events_injected"] >= 1
    rounds = get_recent_debate_rounds("sz000001", "CN")
    assert any("WAR ROOM" in (r.get("evidence_summary") or "") for r in rounds)
    clear_debate_buffer()
