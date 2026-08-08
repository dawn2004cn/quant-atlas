"""Map between unified contracts and execution TradeRequest / exchange dicts."""

from __future__ import annotations

from typing import Any, Mapping

from app.domain.execution.driver_protocol import OrderSide, OrderType, TradeRequest
from app.domain.trading.contracts import OrderRequest, Position, Tick


def order_request_from_trade_request(request: TradeRequest) -> OrderRequest:
    market = str(request.metadata.get("market") or "").strip().upper() or _infer_market(request.symbol)
    side = request.side.value if hasattr(request.side, "value") else str(request.side)
    side_norm = "sell" if str(side).lower() in {"sell", "short"} else "buy"
    ot = request.order_type.value if hasattr(request.order_type, "value") else str(request.order_type)
    ot_norm = "limit" if str(ot).lower() == "limit" else "market"
    price = float(request.price) if ot_norm == "limit" and request.price else None
    return OrderRequest(
        symbol=str(request.symbol),
        market=market,
        side=side_norm,  # type: ignore[arg-type]
        quantity=float(request.amount),
        order_type=ot_norm,  # type: ignore[arg-type]
        price=price,
        client_order_id=str(request.client_order_id or "") or None,
    )


def trade_request_from_order_request(
    request: OrderRequest,
    *,
    account_id: str | None = None,
    exchange: str = "",
) -> TradeRequest:
    side = OrderSide.SELL if request.side == "sell" else OrderSide.BUY
    order_type = OrderType.LIMIT if request.order_type == "limit" else OrderType.MARKET
    meta: dict[str, Any] = {"market": str(request.market).upper()}
    if account_id:
        meta["account_id"] = account_id
    return TradeRequest(
        symbol=request.symbol,
        side=side,
        order_type=order_type,
        amount=float(request.quantity),
        price=float(request.price or 0.0),
        exchange=exchange or _default_exchange(str(request.market)),
        client_order_id=request.client_order_id or "",
        metadata=meta,
    )


def position_from_mapping(data: Mapping[str, Any]) -> Position:
    return Position(
        symbol=str(data.get("symbol") or ""),
        market=str(data.get("market") or "CN"),
        quantity=float(data.get("quantity") or data.get("amount") or 0.0),
        avg_price=float(data.get("avg_price") or data.get("average") or 0.0),
        unrealized_pnl=(
            float(data["unrealized_pnl"])
            if data.get("unrealized_pnl") is not None
            else (float(data["unrealizedPnl"]) if data.get("unrealizedPnl") is not None else None)
        ),
    )


def tick_from_mapping(data: Mapping[str, Any]) -> Tick:
    return Tick(
        symbol=str(data.get("symbol") or ""),
        market=str(data.get("market") or "CN"),
        last=float(data.get("last") or data.get("price") or 0.0),
        bid=float(data["bid"]) if data.get("bid") is not None else None,
        ask=float(data["ask"]) if data.get("ask") is not None else None,
        ts=float(data.get("ts") or data.get("timestamp") or 0.0),
    )


def _infer_market(symbol: str) -> str:
    s = str(symbol or "").upper()
    if "/" in s or "-" in s:
        return "CRYPTO"
    if s.endswith(".HK") or (len(s) == 5 and s.isdigit()):
        return "HK"
    if any(c.isalpha() for c in s.replace(".", "")) and not s.replace(".", "").isdigit():
        return "US"
    return "CN"


def _default_exchange(market: str) -> str:
    m = market.upper()
    if m == "CRYPTO":
        return "binance"
    if m == "US":
        return "alpaca_sim"
    if m == "HK":
        return "futu_sim"
    return "paper_cn"
