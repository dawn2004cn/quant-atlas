"""Unified multi-asset trading contracts (SRS REQ-SRS-03).

Adapters (CCXT / QMT / paper) should map to/from these types at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OrderSide = Literal["buy", "sell"]
OrderTypeName = Literal["market", "limit"]
MarketCode = Literal["CN", "US", "HK", "CRYPTO", "FUT"]


@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    market: MarketCode | str
    side: OrderSide
    quantity: float
    order_type: OrderTypeName
    price: float | None = None
    client_order_id: str | None = None


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    market: MarketCode | str
    quantity: float
    avg_price: float
    unrealized_pnl: float | None = None


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    market: MarketCode | str
    last: float
    bid: float | None
    ask: float | None
    ts: float  # unix seconds
