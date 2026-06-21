from __future__ import annotations
"""Domain entities for trading (Freqtrade port)."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Trade:
    id: int | None = None
    exchange: str = ""
    pair: str = ""
    base_currency: str | None = None
    stake_currency: str | None = None
    is_open: bool = True
    open_date: datetime = field(default_factory=datetime.now)
    open_rate: float = 0.0
    open_rate_requested: float | None = None
    close_date: datetime | None = None
    close_rate: float | None = None
    close_rate_requested: float | None = None
    close_profit: float | None = None
    close_profit_abs: float | None = None
    stake_amount: float = 0.0
    amount: float = 0.0
    stop_loss: float = 0.0
    stop_loss_pct: float | None = 0.0
    initial_stop_loss: float | None = 0.0
    initial_stop_loss_pct: float | None = None
    is_stop_loss_trailing: bool = False
    max_rate: float | None = None
    min_rate: float | None = None
    exit_reason: str | None = None
    strategy: str | None = None
    enter_tag: str | None = None
    leverage: float = 1.0
    is_short: bool = False

    def calc_profit_ratio(self, current_rate: float) -> float:
        """Calculate profit ratio based on current rate."""
        if self.open_rate == 0:
            return 0.0
        if self.is_short:
            return (self.open_rate - current_rate) / self.open_rate
        else:
            return (current_rate - self.open_rate) / self.open_rate

    @property
    def duration_minutes(self) -> float:
        """Calculate trade duration in minutes."""
        end_time = self.close_date or datetime.now()
        return (end_time - self.open_date).total_seconds() / 60.0

    def is_profitable(self, current_rate: float) -> bool:
        """Check if the trade is currently in profit."""
        return self.calc_profit_ratio(current_rate) > 0


@dataclass
class Order:
    id: int | None = None
    ft_trade_id: int | None = None
    order_id: str = ""
    ft_pair: str = ""
    ft_order_side: str = ""
    ft_is_open: bool = True
    ft_amount: float = 0.0
    ft_price: float = 0.0
    status: str | None = None
    symbol: str | None = None
    order_type: str | None = None
    side: str | None = None
    filled: float = 0.0
    remaining: float | None = None
    cost: float | None = None
    order_date: datetime | None = None
    order_filled_date: datetime | None = None

    @property
    def is_fully_filled(self) -> bool:
        """Check if the order is completely filled."""
        if self.ft_amount == 0:
            return False
        return abs(self.filled - self.ft_amount) < 1e-8

    @property
    def filled_ratio(self) -> float:
        """Get the fill percentage (0.0 to 1.0)."""
        if self.ft_amount == 0:
            return 0.0
        return self.filled / self.ft_amount
