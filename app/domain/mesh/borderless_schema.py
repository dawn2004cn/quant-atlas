from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CoolDownReason(str, Enum):
    REVENGE_TRADING = "revenge_trading"
    SENTIMENT_TILT = "sentiment_tilt"


@dataclass
class SplitOrder:
    order_id: str
    quantity: int
    price: float | None = None
    hidden: bool = True
    delay_ms: int = 0


@dataclass
class SymbioticExecutionRequest:
    symbol: str
    market: str
    quantity: int
    user_id: int
    strategy_id: str | None = None
    price: float | None = None
    side: str = "BUY"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoolDownDecision:
    suggested_delay: int
    reason: CoolDownReason
    triggers: list[str] = field(default_factory=list)


@dataclass
class SymbioticExecutionResult:
    ok: bool
    error: str | None = None
    cool_down_reason: CoolDownReason | None = None
    suggested_delay_seconds: int | None = None
    sentiment_triggers: list[str] = field(default_factory=list)
    splits: list[SplitOrder] | list[dict[str, Any]] = field(default_factory=list)
    child_count: int = 0
