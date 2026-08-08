"""Adapter skeleton status tests (P2)."""

import pytest

from app.domain.trading.contracts import OrderRequest
from app.infrastructure.adapters.ctp_adapter import CTPAdapter
from app.infrastructure.adapters.ibkr_adapter import AdapterNotReadyError, IBKRAdapter


def test_ibkr_status_not_ready():
    a = IBKRAdapter()
    st = a.status()
    assert st["ready"] is False
    assert st["phase"] == "P2"
    assert st["sim_ready"] is True
    assert "connection" in st


def test_ctp_status_points_to_qmt():
    a = CTPAdapter()
    st = a.status()
    assert st["near_term"] == "QMT"
    assert st["ready"] is False
    assert st["sim_ready"] is True


def test_ibkr_submit_simulation_by_default():
    a = IBKRAdapter()
    oid = a.submit_order(
        OrderRequest(symbol="AAPL", market="US", side="buy", quantity=1, order_type="market"),
    )
    assert oid.startswith("IBKR_SIM_")


def test_ibkr_submit_raises_when_sim_disabled():
    a = IBKRAdapter(allow_simulation=False)
    with pytest.raises(AdapterNotReadyError):
        a.submit_order(
            OrderRequest(symbol="AAPL", market="US", side="buy", quantity=1, order_type="market"),
        )


def test_ibkr_live_dry_run_default_real_off():
    a = IBKRAdapter(live_submit=True, allow_real_orders=False)
    oid = a.submit_order(
        OrderRequest(symbol="AAPL", market="US", side="buy", quantity=1, order_type="market"),
    )
    assert oid.startswith("IBKR_LIVE_")
