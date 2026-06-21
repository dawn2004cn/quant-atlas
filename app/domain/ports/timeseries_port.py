"""Time-series database port — pure interface for dependency inversion.

This module defines the abstract ``TimeSeriesDBPort`` interface that the
application layer depends on.  Concrete implementations (QuestDB, ClickHouse,
in-memory) live in ``infrastructure.timeseries.adapters``.

Why this file:
    Domain ports must never import infrastructure code.  The original
    ``timeseries_ports.py`` had QuestDBAdapter / ClickHouseAdapter concrete
    classes that imported ``infrastructure.timeseries.ohlcv_history_reader``
    directly inside their ``query_ohlcv()`` methods — a textbook DIP violation.

    The clean architecture solution:
      1. Abstract port lives here (domain layer).
      2. Concrete implementations live in infrastructure layer.
      3. Infrastructure wiring factory lives in
         ``infrastructure.timeseries.adapters``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TimeSeriesPoint:
    """A single time-series data point."""

    timestamp: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    fields: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.fields is None:
            self.fields = {}


class TimeSeriesDBPort(ABC):
    """Port for time-series database operations (QuestDB, ClickHouse).

    The application layer depends on this interface; infrastructure
    provides concrete implementations via the factories in
    ``infrastructure.timeseries.adapters``.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the time-series database.

        Returns True on success, False otherwise.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the time-series database."""
        ...

    @abstractmethod
    def write_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        data: list[TimeSeriesPoint],
    ) -> int:
        """Write OHLCV data, return number of rows written."""
        ...

    @abstractmethod
    def query_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query OHLCV data between start_date and end_date.

        Args:
            symbol: Stock symbol.
            timeframe: e.g. "D" for daily bars.
            start_date: ISO date string (YYYY-MM-DD).
            end_date: ISO date string (YYYY-MM-DD).
            limit: Maximum rows to return.

        Returns:
            List of bar dicts with keys like ``date``, ``open``, ``high``,
            ``low``, ``close``, ``volume``, ``amount``.
        """
        ...

    @abstractmethod
    def execute_raw_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a raw SQL query and return results."""
        ...
