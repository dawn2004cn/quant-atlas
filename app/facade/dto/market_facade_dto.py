"""Market facade request/response DTOs."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class HistoryBarsQueryDTO(BaseModel):
    """Validated parameters for historical bar queries."""

    symbol: str = Field(..., min_length=1, max_length=32)
    market: str = Field(default="CN", min_length=2, max_length=8)
    start_date: str | None = None
    end_date: str | None = None
    count: int = Field(default=100, ge=1, le=10000)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        return symbol

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not _DATE_RE.match(value):
            raise ValueError(f"Invalid date format (YYYY-MM-DD): {value}")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> HistoryBarsQueryDTO:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class MarketQuotesQueryDTO(BaseModel):
    """Validated parameters for batch quote listing."""

    market: str = Field(default="CN", min_length=2, max_length=8)
    symbols: list[str] | None = None

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [s.strip().upper() for s in value if s and s.strip()]
        return normalized or None


class MarketPanoramaDTO(BaseModel):
    """Loose panorama envelope; extra service fields are preserved."""

    model_config = ConfigDict(extra="allow")

    market_status: str | None = None
    sentiment_score: float | None = None

    @classmethod
    def from_service(cls, payload: Any, *, market: str | None = None) -> MarketPanoramaDTO:
        from app.domain.dto.quote_factory import canonical_panorama_dict

        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        elif isinstance(payload, dict):
            data = payload
        else:
            data = dict(payload)
        data = canonical_panorama_dict(data, market=market)
        return cls.model_validate(data)
