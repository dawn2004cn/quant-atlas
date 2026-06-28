from __future__ import annotations

"""Port for recording and querying data fetch lineage."""

from typing import Any, Protocol


class DataLineagePort(Protocol):
    def record_fetch(self, symbol: str, source: str, timestamp: str, rows: int) -> str:
        ...

    def get_lineage(self, symbol: str, date: str) -> list[dict[str, Any]]:
        ...
