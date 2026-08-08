"""IBKR / CTP adapter contract + simulation + live dry-run tests."""

from __future__ import annotations

import pytest

from app.domain.trading.contracts import OrderRequest, Position, Tick
from app.infrastructure.adapters.broker_connection import tcp_reachable
from app.infrastructure.adapters.broker_session import FakeBrokerSession
from app.infrastructure.adapters.ctp_adapter import CTPAdapter
from app.infrastructure.adapters.ibkr_adapter import AdapterNotReadyError, IBKRAdapter
from app.infrastructure.execution.adapter_registry import list_execution_adapters
from app.modules.execution.services.ibkr_ctp_integration_probe import (
    run_ibkr_ctp_integration_probe,
)
from app.modules.execution.services.risk_guard_service import (
    AccountRiskSnapshot,
    InMemoryRiskGuardStore,
    RiskGuardBlockedError,
    RiskGuardService,
)


def _sample_order(*, market: str = "US", symbol: str = "AAPL") -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        market=market,
        side="buy",
        quantity=10.0,
        order_type="limit",
        price=100.0,
        client_order_id="qa-contract-1",
    )


def test_tcp_reachable_missing_host():
    assert tcp_reachable("", 7497)["ok"] is False


def test_ibkr_status_contract_fields():
    st = IBKRAdapter(allow_simulation=True, live_submit=False).status()
    assert st["adapter_id"] == "ibkr"
    assert st["ready"] is False
    assert st["sim_ready"] is True
    assert st["phase"] == "P2"
    assert "connection" in st
    assert "message" in st


def test_ctp_status_contract_fields():
    st = CTPAdapter(broker_id="b", user_id="u", password="x", allow_simulation=True).status()
    assert st["adapter_id"] == "ctp"
    assert st["ready"] is False
    assert st["sim_ready"] is True
    assert st["near_term"] == "QMT"
    assert st["credentials_configured"] is True
    assert st.get("connection", {}).get("td_ok") is False


def test_ibkr_simulation_accepts_order_request():
    a = IBKRAdapter(allow_simulation=True, live_submit=False)
    oid = a.submit_order(_sample_order())
    assert oid.startswith("IBKR_SIM_")
    assert len(a.list_sim_orders()) == 1
    tick = a.get_tick("AAPL")
    assert isinstance(tick, Tick)
    assert tick.last == 100.0
    assert a.get_positions() == []


def test_ctp_simulation_accepts_order_request():
    a = CTPAdapter(allow_simulation=True, live_submit=False)
    oid = a.submit_order(_sample_order(market="FUT", symbol="IF2509"))
    assert oid.startswith("CTP_SIM_")
    assert a.list_sim_orders()[0]["symbol"] == "IF2509"


def test_ibkr_live_dry_run_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.adapters.ibkr_adapter._repo_instance",
        lambda *parts: tmp_path.joinpath(*parts),
    )
    a = IBKRAdapter(allow_simulation=True, live_submit=True, allow_real_orders=False)
    oid = a.submit_order(_sample_order())
    assert oid.startswith("IBKR_LIVE_")
    files = list(tmp_path.joinpath("ibkr_orders").glob("*.json"))
    assert files, "expected dry-run persistence"


def test_ibkr_real_without_sdk_raises(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.adapters.ibkr_adapter.detect_ib_insync",
        lambda: {"installed": False, "module": "ib_insync"},
    )
    a = IBKRAdapter(allow_simulation=True, live_submit=True, allow_real_orders=True)
    with pytest.raises(AdapterNotReadyError, match="ib_insync"):
        a.submit_order(_sample_order())


def test_ibkr_real_injected_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.adapters.ibkr_adapter._repo_instance",
        lambda *parts: tmp_path.joinpath(*parts),
    )
    session = FakeBrokerSession(prefix="IBKR_TWS")
    a = IBKRAdapter(
        allow_simulation=True,
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        port=7497,
        session=session,
    )
    oid = a.submit_order(_sample_order())
    assert oid.startswith("IBKR_TWS_")
    assert (tmp_path / "ibkr_orders" / f"{oid}.json").exists()


def test_ibkr_live_port_requires_confirm():
    session = FakeBrokerSession(prefix="IBKR_TWS")
    a = IBKRAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        port=7496,
        session=session,
    )
    with pytest.raises(AdapterNotReadyError, match="live_account_not_confirmed"):
        a.submit_order(_sample_order())


def test_ctp_real_requires_confirm_then_injected_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.adapters.ibkr_adapter._repo_instance",
        lambda *parts: tmp_path.joinpath(*parts),
    )
    session = FakeBrokerSession(prefix="CTP_TD")
    blocked = CTPAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        session=session,
    )
    with pytest.raises(AdapterNotReadyError, match="ctp_live_account_not_confirmed"):
        blocked.submit_order(_sample_order(market="FUT", symbol="IF2509"))
    a = CTPAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=True,
        session=session,
    )
    oid = a.submit_order(_sample_order(market="FUT", symbol="IF2509"))
    assert oid.startswith("CTP_TD_")


def test_ibkr_sim_disabled_raises():
    a = IBKRAdapter(allow_simulation=False, live_submit=False)
    with pytest.raises(AdapterNotReadyError, match="ibkr"):
        a.submit_order(_sample_order())
    with pytest.raises(AdapterNotReadyError):
        a.get_positions()


def test_ctp_sim_disabled_raises():
    a = CTPAdapter(allow_simulation=False)
    with pytest.raises(AdapterNotReadyError, match="ctp"):
        a.submit_order(_sample_order(market="FUT", symbol="IF2509"))
    with pytest.raises(AdapterNotReadyError):
        a.get_positions()


def test_ibkr_simulation_honors_risk_guard(monkeypatch):
    store = InMemoryRiskGuardStore()
    store.set_snapshot("ibkr_sim", AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0))
    guard = RiskGuardService(store=store)
    monkeypatch.setattr(
        "app.modules.execution.services.risk_guard_factory.get_risk_guard_service",
        lambda **kwargs: guard,
    )
    monkeypatch.setattr(
        "app.modules.execution.services.risk_guard_factory.risk_guard_enabled",
        lambda: True,
    )
    a = IBKRAdapter(allow_simulation=True, live_submit=False)
    with pytest.raises(RiskGuardBlockedError):
        a.submit_order(_sample_order())


def test_registry_lists_ibkr_ctp_sim_ready():
    rows = {r["adapter_id"]: r for r in list_execution_adapters()}
    assert "ibkr" in rows and rows["ibkr"]["ready"] is False
    assert "ctp" in rows and rows["ctp"]["ready"] is False
    assert rows["ibkr"].get("sim_ready") is True
    assert rows["ctp"].get("sim_ready") is True
    assert rows["ibkr"]["contracts"] is True
    assert rows["qmt"]["market"] == "CN"
    assert "connection" in (rows["ibkr"].get("detail") or {})


def test_integration_probe_passes_required():
    report = run_ibkr_ctp_integration_probe()
    payload = report.as_dict()
    assert payload["ok"], payload
    assert payload["passed"] >= 6
    assert payload["failed"] == 0


def test_order_request_is_frozen_contract():
    req = _sample_order()
    assert req.side == "buy"
    with pytest.raises(Exception):
        req.quantity = 99  # type: ignore[misc]


def test_position_tick_dataclasses_exist_for_adapters():
    pos = Position(symbol="AAPL", market="US", quantity=1.0, avg_price=10.0)
    tick = Tick(symbol="AAPL", market="US", last=10.5, bid=10.4, ask=10.6, ts=0.0)
    assert pos.quantity == 1.0
    assert tick.last == 10.5
