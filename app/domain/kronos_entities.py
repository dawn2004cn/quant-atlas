from __future__ import annotations
"""Domain entities for Kronos foundation model integration."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KronosModel:
    model_id: str
    model_type: str  # mini, small, base
    hf_path: str | None = None
    local_path: str | None = None
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class KronosPrediction:
    id: int | None = None
    ticker: str = ""
    model_id: str = ""
    prediction_date: datetime = field(default_factory=datetime.now)
    horizon_days: int = 0
    forecast_data: list[dict[str, Any]] = field(default_factory=list)
    actual_data: list[dict[str, Any]] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
