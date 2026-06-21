"""Market data DTOs."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MarketDataDTO:
    """Generic market data transfer object."""

    symbol: str = ""
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
