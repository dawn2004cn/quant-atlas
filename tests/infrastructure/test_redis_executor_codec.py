"""Redis executor codec unit tests."""

from app.infrastructure.execution.driver.protocol import (
    OrderSide,
    OrderStatus,
    OrderType,
    TradeRequest,
    TradeResponse,
)
from app.infrastructure.execution.driver.redis_executor_codec import (
    decode_trade_request,
    decode_trade_response,
    encode_cancel_payload,
    encode_trade_request,
    order_status_key,
    result_key_for,
)


def test_encode_decode_trade_request() -> None:
    request = TradeRequest(
        symbol="600519",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        amount=100.0,
        price=1800.0,
    )
    restored = decode_trade_request(encode_trade_request(request))
    assert restored.symbol == "600519"
    assert restored.side == OrderSide.BUY
    assert restored.amount == 100.0


def test_encode_cancel_payload() -> None:
    payload = encode_cancel_payload("ord-1", "BTCUSDT")
    assert "cancel" in payload
    assert "ord-1" in payload


def test_key_helpers() -> None:
    assert order_status_key("abc") == "order_status:abc"
    assert result_key_for("execution_result:", "req_1") == "execution_result:req_1"


def test_decode_trade_response() -> None:
    raw = TradeResponse(
        request_id="r1",
        order_id="o1",
        status=OrderStatus.FILLED,
    ).to_dict()
    import json

    response = decode_trade_response(json.dumps(raw))
    assert response.order_id == "o1"
    assert response.status == OrderStatus.FILLED
