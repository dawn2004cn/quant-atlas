"""QMT executor simulation labeling tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.infrastructure.execution.qmt_executor import QMTExecutor, qmt_executor_status


def test_qmt_executor_status_defaults_to_simulation():
    status = qmt_executor_status(account_id="acc1", qmt_path="/qmt")
    assert status["execution_mode"] == "simulation"
    assert status["live_submit"] is False
    assert status["warning"]


def test_qmt_executor_status_live_when_enabled():
    status = qmt_executor_status(
        account_id="acc1",
        qmt_path="/qmt",
        live_submit=True,
    )
    assert status["execution_mode"] == "live"
    assert status["xtquant_required"] is True


def test_qmt_execute_simulation_without_xtquant():
    ex = QMTExecutor(account_id="demo", qmt_path="/qmt", live_submit=False)
    signal = TradeSignalDTO(
        symbol="600519",
        direction=SignalDirection.BUY,
        quantity=100,
        price=1500.0,
        strategy_id="test_strategy",
    )
    order_id = ex.execute(signal)
    assert order_id.startswith("QMT_")
    pending = ex.get_pending_orders()[order_id]
    assert pending["simulation"] is True
    assert pending["gateway"] == "qmt"


def test_qmt_live_submit_requires_xtquant():
    ex = QMTExecutor(account_id="demo", qmt_path="/qmt", live_submit=True)
    signal = TradeSignalDTO(
        symbol="600519",
        direction=SignalDirection.BUY,
        quantity=100,
        price=1500.0,
        strategy_id="test_strategy",
    )
    with patch.dict("sys.modules", {"xtquant": None}):
        with pytest.raises((RuntimeError, ImportError)):
            ex.execute(signal)
