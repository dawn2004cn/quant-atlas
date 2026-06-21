from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketDepthSnapshot:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
