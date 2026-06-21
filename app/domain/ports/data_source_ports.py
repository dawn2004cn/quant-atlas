"""Consolidated data source ports (CN fundamentals, sector boards, cache)."""

from __future__ import annotations

from typing import Any, Protocol


# ── CN Fundamentals ─────────────────────────────────────────────────────


class CnFundamentalsPort(Protocol):
    """Port for Chinese financial fundamentals data."""

    def get_financials(self, symbol: str) -> dict[str, Any]:
        ...

    def get_indicators(self, symbol: str) -> dict[str, Any]:
        ...


# ── Sector Board ────────────────────────────────────────────────────────


class CnSectorBoardPort(Protocol):
    """Port for Chinese sector board (板块) data."""

    def get_sector_stocks(self, sector: str) -> list[str]:
        ...

    def get_stock_sectors(self, symbol: str) -> list[str]:
        ...


# ── Hot Sector ──────────────────────────────────────────────────────────


class HotSectorStoragePort(Protocol):
    """Port for hot sector (热股) storage."""

    def get_hot_sectors(self, date: str) -> list[dict[str, Any]]:
        ...

    def save_hot_sectors(self, date: str, data: list[dict[str, Any]]) -> bool:
        ...


# ── Cache Ports ─────────────────────────────────────────────────────────


class StockCachePort(Protocol):
    """Port for stock-level caching."""

    def get(self, symbol: str, key: str) -> Any | None:
        ...

    def set(self, symbol: str, key: str, value: Any, ttl: int = 3600) -> None:
        ...


class QuoteCachePort(Protocol):
    """Port for quote-level caching."""

    def get_quote(self, symbol: str, market: str) -> dict[str, Any] | None:
        ...

    def set_quote(self, symbol: str, market: str, data: dict[str, Any], ttl: int = 60) -> None:
        ...
