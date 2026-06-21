from __future__ import annotations
"""Domain entities for QuantML integration."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QuantMLFactor:
    id: int | None = None
    factor_name: str = ""
    category: str | None = None
    ic_mean: float | None = None
    icir: float | None = None
    long_average: float | None = None
    long_short: float | None = None
    t_stat: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
