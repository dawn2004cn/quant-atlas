from __future__ import annotations
"""Market data domain events."""

from dataclasses import dataclass
from app.domain.events.bus import DomainEvent

@dataclass
class MarketDataIngestedEvent(DomainEvent):
    """Fired when new market data is ingested."""
    symbol: str
    data_type: str
    count: int
