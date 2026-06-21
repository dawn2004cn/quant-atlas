from __future__ import annotations

"""TradeRequest / TradeResponse Redis 载荷编解码与 key 命名。"""

import json

from .protocol import TradeRequest, TradeResponse


def encode_trade_request(request: TradeRequest) -> str:
    return json.dumps(request.to_dict())


def decode_trade_request(payload: str) -> TradeRequest:
    return TradeRequest.from_dict(json.loads(payload))


def encode_cancel_payload(order_id: str, symbol: str) -> str:
    return json.dumps({"action": "cancel", "order_id": order_id, "symbol": symbol})


def order_status_key(order_id: str) -> str:
    return f"order_status:{order_id}"


def result_key_for(prefix: str, request_id: str) -> str:
    return f"{prefix}{request_id}"


def decode_trade_response(raw: str) -> TradeResponse:
    return TradeResponse.from_dict(json.loads(raw))
