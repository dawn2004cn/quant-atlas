from __future__ import annotations

"""Infrastructure adapter for ``DataLineagePort``."""

from typing import Any

from app.domain.ports.data_lineage_port import DataLineagePort
from app.infrastructure.data_quality.monitor import DataLineageTracker


class DataLineagePortAdapter(DataLineagePort):
    def __init__(self, tracker: DataLineageTracker | None = None) -> None:
        self._tracker = tracker or DataLineageTracker()

    def record_fetch(self, symbol: str, source: str, timestamp: str, rows: int) -> str:
        return self._tracker.record_fetch(symbol, source, timestamp, rows)

    def get_lineage(self, symbol: str, date: str) -> list[dict[str, Any]]:
        return self._tracker.get_lineage(symbol, date)
