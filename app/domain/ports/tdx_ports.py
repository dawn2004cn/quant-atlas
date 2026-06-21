"""Consolidated TDX (通达信) data ports.

Aggregates all TDX-related port interfaces that were previously scattered
across multiple single-purpose files.  Infrastructure adapters implement
these consolidated protocols.
"""

from __future__ import annotations

from typing import Any, Protocol


class TdxLocalFilePort(Protocol):
    """Port for reading local TDX data files."""

    def read_local_data(self, symbol: str, data_type: str) -> dict[str, Any]:
        ...


class TdxDaykWritePort(Protocol):
    """Port for writing daily K-line data via TDX."""

    def write_dayk(self, symbol: str, data: list[dict[str, Any]]) -> int:
        ...


class TdxDaykSyncSessionPort(Protocol):
    """Port for synchronized TDX dayk writes."""

    def sync_write(self, symbol: str, data: list[dict[str, Any]]) -> bool:
        ...


class TdxBaseDataWritePort(Protocol):
    """Port for base data writes via TDX."""

    def write_base(self, symbol: str, data: dict[str, Any]) -> bool:
        ...


class TdxGpcwRepository(Protocol):
    """Port for TDX GPCW (财务报表) data."""

    def get_gpcw(self, symbol: str, year: int) -> list[dict[str, Any]]:
        ...


class TdxFinancePort(Protocol):
    """Port for TDX finance snapshot data."""

    def fetch_snapshot(self, symbol: str) -> dict[str, Any]:
        ...


class TdxBlockReadPort(Protocol):
    """Port for reading TDX block/sector files."""

    def read_block(self, block_name: str) -> list[str]:
        ...


class PytdxMarketPort(Protocol):
    """Port for Pytdx market data access."""

    def get_realtime_quote(self, market: str, symbol: str) -> dict[str, Any]:
        ...

    def get_history_kline(
        self, market: str, symbol: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        ...
