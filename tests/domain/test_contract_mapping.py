"""Tests for OrderRequest / TradeRequest mapping."""

from app.domain.execution.driver_protocol import OrderSide, OrderType, TradeRequest
from app.domain.trading.contract_mapping import (
    order_request_from_trade_request,
    position_from_mapping,
    tick_from_mapping,
    trade_request_from_order_request,
)
from app.domain.trading.contracts import OrderRequest


def test_roundtrip_trade_request_order_request():
    tr = TradeRequest(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        amount=0.01,
        price=60000.0,
        metadata={"market": "CRYPTO", "account_id": "a1"},
    )
    req = order_request_from_trade_request(tr)
    assert isinstance(req, OrderRequest)
    assert req.symbol == "BTC/USDT"
    assert req.market == "CRYPTO"
    assert req.side == "buy"
    assert req.quantity == 0.01
    back = trade_request_from_order_request(req, account_id="a1")
    assert back.symbol == "BTC/USDT"
    assert back.amount == 0.01
    assert back.metadata.get("market") == "CRYPTO"


def test_position_and_tick_helpers():
    p = position_from_mapping({"symbol": "AAPL", "market": "US", "quantity": 10, "avg_price": 180})
    t = tick_from_mapping({"symbol": "AAPL", "market": "US", "last": 181, "bid": 180.9, "ask": 181.1, "ts": 1.0})
    assert p.quantity == 10
    assert t.last == 181
