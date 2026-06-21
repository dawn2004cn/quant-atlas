from __future__ import annotations
"""Domain entities for global market data (OpenBB port)."""


import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GlobalQuote:
    symbol: str
    asset_class: str  # equity, fx, crypto
    provider: str
    price: float = 0.0
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    currency: str = "USD"
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProviderConfig:
    provider_name: str
    is_enabled: bool = True
    settings: dict = field(default_factory=dict)
    updated_at: datetime | None = None
