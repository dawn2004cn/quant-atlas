from __future__ import annotations
"""Global market DTOs for standardized data transfer."""


from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GlobalQuoteDTO(BaseModel):
    """DTO for global market quote data."""
    symbol: str
    name: str
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market: str = ""
    source: str = "openbb"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class GlobalHistoryDTO(BaseModel):
    """DTO for global market historical data."""
    symbol: str
    market: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class GlobalMarketConfigDTO(BaseModel):
    """DTO for global market provider configuration."""
    provider_name: str
    settings: dict[str, Any] = Field(default_factory=dict)
