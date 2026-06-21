from __future__ import annotations
"""Port for market data quality validation."""

from typing import Any, Protocol


class DataQualityPort(Protocol):
    def validate(self, data: Any) -> list[Any]:
        ...
