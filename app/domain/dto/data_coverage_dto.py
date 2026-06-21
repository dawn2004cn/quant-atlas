from __future__ import annotations

from pydantic import BaseModel, Field


class DataCoverageDTO(BaseModel):
    symbol: str = ""
    market: str = "CN"
    lookback_days: int = 30
    expected_sessions: int = 0
    actual_sessions: int = 0
    coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    latest_bar_date: str = ""
    stale_session_gap: int = 0
    level: str = "unknown"
    warning: str = ""
    confidence_penalty: float = Field(default=0.0, ge=0.0, le=0.5)


__all__ = ["DataCoverageDTO"]
