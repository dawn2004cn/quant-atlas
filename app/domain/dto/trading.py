from __future__ import annotations

"""Extended DTO contracts for trading and execution."""


from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    """Time in force."""
    DAY = "day"
    GTC = "good_till_cancel"
    IOC = "immediate_or_cancel"
    FOK = "fill_or_kill"


class ExecutionResult(str, Enum):
    """Execution result."""
    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class TradeSide(str, Enum):
    """Trade side."""
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"


class ExecutionReportContract(BaseModel):
    """Execution report contract."""
    order_id: str
    order_local_id: str
    code: str
    name: str = ""
    side: TradeSide
    order_type: OrderType
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    filled_quantity: int = Field(default=0, ge=0)
    filled_price: float = Field(default=0, ge=0)
    avg_price: float = Field(default=0, ge=0)
    status: str
    message: str = ""
    commission: float = Field(default=0, ge=0)
    slippage: float = Field(default=0)
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def fill_rate(self) -> float:
        if self.quantity == 0:
            return 0
        return round(self.filled_quantity / self.quantity * 100, 2)

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.filled_quantity >= self.quantity


class PreTradeValidationContract(BaseModel):
    """Pre-trade validation contract."""
    code: str
    side: TradeSide
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)

    cash_available: float = Field(gt=0)
    position_quantity: int = Field(default=0, ge=0)
    max_position_pct: float = Field(ge=0, le=1)
    max_single_order_pct: float = Field(ge=0, le=1)
    blacklist: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def order_value(self) -> float:
        return self.quantity * self.price

    @computed_field
    @property
    def validation_errors(self) -> list[str]:
        errors = []

        if self.code in self.blacklist:
            errors.append(f"Stock {self.code} is in blacklist")

        if self.side in [TradeSide.BUY, TradeSide.COVER]:
            required_cash = self.order_value
            if required_cash > self.cash_available:
                errors.append(f"Insufficient cash: {required_cash} > {self.cash_available}")

        order_pct = self.order_value / self.cash_available if self.cash_available > 0 else 0
        if order_pct > self.max_single_order_pct:
            errors.append(f"Order value {order_pct*100:.1f}% exceeds max {self.max_single_order_pct*100}%")

        return errors

    @computed_field
    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0


class AccountStateContract(BaseModel):
    """Account state contract."""
    account_id: str
    total_assets: float = Field(gt=0)
    cash: float = Field(ge=0)
    market_value: float = Field(ge=0)
    frozen_cash: float = Field(default=0, ge=0)
    available_cash: float = Field(ge=0)
    positions_value: float = Field(ge=0)
    positions_count: int = Field(default=0, ge=0)
    today_pnl: float = 0.0
    today_pnl_pct: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    margin_used: float = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)


class BacktestConfigContract(BaseModel):
    """Backtest configuration contract."""
    initial_capital: float = Field(default=100000, gt=0)
    commission_rate: float = Field(default=0.0003, ge=0, le=0.01)
    slippage: float = Field(default=0.001, ge=0, le=0.1)
    start_date: str
    end_date: str
    codes: list[str] = Field(min_length=1)
    frequency: str = Field(default="daily", description="daily, weekly, monthly")
    benchmark: str | None = None


class BacktestResultContract(BaseModel):
    """Backtest result contract."""
    id: str
    name: str
    config: BacktestConfigContract

    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    annual_return: float = 0.0
    annual_volatility: float = 0.0

    start_date: str
    end_date: str
    completed_at: datetime = Field(default_factory=datetime.now)


class FactorContract(BaseModel):
    """Factor definition contract."""
    name: str
    category: str
    description: str = ""
    formula: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class FactorValueContract(BaseModel):
    """Factor value contract."""
    code: str
    factor_name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.now)


class AlertContract(BaseModel):
    """Alert contract."""
    id: str
    code: str
    type: str
    level: str = Field(description="info, warning, error, critical")
    title: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    acknowledged: bool = False


__all__ = [
    "OrderType",
    "TimeInForce",
    "ExecutionResult",
    "TradeSide",
    "ExecutionReportContract",
    "PreTradeValidationContract",
    "AccountStateContract",
    "BacktestConfigContract",
    "BacktestResultContract",
    "FactorContract",
    "FactorValueContract",
    "AlertContract",
]
