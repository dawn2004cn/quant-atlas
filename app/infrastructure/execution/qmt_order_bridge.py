"""Bridge unified OrderRequest and QMT TradeSignalDTO."""

from __future__ import annotations

from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.domain.trading.contracts import OrderRequest


def trade_signal_from_order_request(
    request: OrderRequest,
    *,
    strategy_id: str = "qmt_bridge",
    user_id: int | None = None,
) -> TradeSignalDTO:
    direction = SignalDirection.SELL if request.side == "sell" else SignalDirection.BUY
    price = float(request.price if request.price is not None else 0.0)
    qty = int(abs(request.quantity))
    return TradeSignalDTO(
        symbol=str(request.symbol),
        direction=direction,
        price=price,
        quantity=max(qty, 0),
        strategy_id=strategy_id,
        user_id=user_id,
        reasoning=f"order_request:{request.order_type}:{request.client_order_id or ''}",
    )


def order_request_from_trade_signal(
    signal: TradeSignalDTO,
    *,
    market: str = "CN",
    order_type: str = "limit",
) -> OrderRequest:
    side = "sell" if signal.direction in (SignalDirection.SELL, SignalDirection.SHORT) else "buy"
    return OrderRequest(
        symbol=signal.symbol,
        market=market,
        side=side,  # type: ignore[arg-type]
        quantity=float(signal.quantity),
        order_type="limit" if order_type == "limit" else "market",  # type: ignore[arg-type]
        price=float(signal.price),
        client_order_id=None,
    )
