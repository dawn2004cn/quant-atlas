"""QMT OrderRequest bridge tests."""

from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.domain.trading.contracts import OrderRequest
from app.infrastructure.execution.qmt_executor import QMTExecutor
from app.infrastructure.execution.qmt_order_bridge import (
    order_request_from_trade_signal,
    trade_signal_from_order_request,
)


def test_order_request_roundtrip_with_signal():
    req = OrderRequest(
        symbol="600519",
        market="CN",
        side="buy",
        quantity=100,
        order_type="limit",
        price=1800.0,
        client_order_id="c1",
    )
    signal = trade_signal_from_order_request(req)
    assert signal.symbol == "600519"
    assert signal.direction == SignalDirection.BUY
    assert signal.quantity == 100
    back = order_request_from_trade_signal(signal, market="CN")
    assert back.side == "buy"
    assert back.quantity == 100


def test_qmt_executor_execute_order_request_simulation():
    ex = QMTExecutor(account_id="demo", qmt_path="", live_submit=False)
    req = OrderRequest(
        symbol="000001",
        market="CN",
        side="buy",
        quantity=100,
        order_type="limit",
        price=10.0,
    )
    order_id = ex.execute_order_request(req)
    assert order_id.startswith("QMT_")
