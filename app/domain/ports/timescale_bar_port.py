from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class TimescaleBarPort(Protocol):
    """OHLCV 时序库（TimescaleDB ``market_bars`` hypertable）。"""

    def ensure_schema(self) -> None:
        ...

    def open_sync_session(self) -> Any:
        """Per-thread 批量写入会话（TDX 同步路径复用连接）。"""
        ...

    def upsert_bars(
        self,
        *,
        symbol: str,
        market: str,
        bars: list[dict[str, Any]],
        source: str = "",
    ) -> int:
        ...

    def upsert_ohlcv_package(
        self,
        *,
        symbol: str,
        market: str,
        raw_rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
        source: str = "",
    ) -> dict[str, int]:
        ...

    def get_bars(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 5000,
        adjust: str = "raw",
    ) -> list[dict[str, Any]]:
        ...

    def get_factors(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        ...

    def refresh_adjusted_materialized_views(self, *, concurrently: bool = True) -> None:
        """写入 raw+因子后刷新前/后复权物化视图。"""
        ...
