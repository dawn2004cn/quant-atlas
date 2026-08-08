"""Tests for unified trading contracts (REQ-SRS-03)."""

from app.domain.trading.contracts import OrderRequest, Position, Tick


def test_order_request_frozen():
    o = OrderRequest(symbol="600519", market="CN", side="buy", quantity=100.0, order_type="limit", price=1800.0)
    assert o.symbol == "600519"
    assert o.side == "buy"
    try:
        o.quantity = 1  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised


def test_position_and_tick():
    p = Position(symbol="BTC/USDT", market="CRYPTO", quantity=0.1, avg_price=60000.0)
    t = Tick(symbol="BTC/USDT", market="CRYPTO", last=61000.0, bid=60990.0, ask=61010.0, ts=1.0)
    assert p.unrealized_pnl is None
    assert t.last == 61000.0
