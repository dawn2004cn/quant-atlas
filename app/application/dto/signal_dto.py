from __future__ import annotations
"""DTOs for Signal Flag services."""


from typing import Any
from pydantic import BaseModel, Field


class SignalFlagQueryDTO(BaseModel):
    """DTO for querying signal flags."""
    market: str = Field(default="CN", description="Market code")
    symbols: list[str] | None = Field(default=None, description="List of symbols")
    max_stocks: int = Field(default=100, ge=1, le=5000, description="Max stocks to query")


class SignalFlagBackfillDTO(BaseModel):
    """DTO for backfilling signal flags."""
    market: str = Field(default="CN", description="Market code")
    symbols: list[str] = Field(..., min_length=1, description="List of symbols")
    force: bool = Field(default=False, description="Force backfill")


class SignalFlagUpdateDTO(BaseModel):
    """DTO for updating signal flag."""
    symbol: str = Field(..., description="Stock symbol")
    flag_value: Any = Field(..., description="Flag value")
    reason: str | None = Field(default=None, description="Update reason")
