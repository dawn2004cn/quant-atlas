from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionProfile:
    order_id: str
    symbol: str
    quantity: int
    price: float | None
    user_id: int
    strategy_id: str
    timestamp: str

    def route_by(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price": self.price,
            "user_id": self.user_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
        }
