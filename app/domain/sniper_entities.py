from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "side"

@dataclass
class SniperSelection:
    symbol: str
    name: str
    strategy_name: str
    regime: MarketRegime
    commander_reason: str
    agent_consensus: dict[str, Any]
    initial_price: float
    current_price: float
    shares: int
    stop_loss: float
    take_profit: float
    status: str = "holding"
    pnl_amount: float = 0.0
    pnl_pct: float = 0.0
    id: int | None = None
    selected_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def market_value(self) -> float:
        return self.current_price * self.shares
