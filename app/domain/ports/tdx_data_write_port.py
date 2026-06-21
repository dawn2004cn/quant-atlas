from __future__ import annotations

from typing import Any, Protocol


class TdxDaykSyncSessionPort(Protocol):
    """Single-connection batch session for TDX day-K sync."""

    def batch_get_latest_dates(self, stock_codes: list[str]) -> dict[str, str | None]:
        ...

    def write_bars(self, stock_code: str, rows: list[dict[str, Any]]) -> int:
        ...

    def write_factors(self, stock_code: str, factors: list[dict[str, Any]]) -> int:
        ...

    def commit(self) -> None:
        ...

    def close(self) -> None:
        ...


class TdxDaykWritePort(Protocol):
    def open_sync_session(
        self,
        *,
        table_suffix: str = "",
        insert_only: bool = False,
    ) -> TdxDaykSyncSessionPort:
        ...

    def list_history_calendar_dates(self) -> list[str]:
        ...

    def list_history_stock_codes(self, *, limit: int | None = None) -> list[str]:
        ...

    def fetch_history_rows(self, table: str, codes: list[str]) -> list[dict[str, Any]]:
        ...

    def fetch_history_rows_for_code(
        self,
        stock_code: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def list_stock_codes_updated_since(
        self,
        since_date: str,
        *,
        limit: int | None = None,
    ) -> list[str]:
        ...


class TdxBaseIngestCounts(Protocol):
    stocks_upserted: int
    blocks_upserted: int
    block_items_upserted: int
    watchlists_upserted: int
    watchlist_items_upserted: int
    watchlist_items_added: int
    watchlist_items_skipped: int
    finance_upserted: int
    finance_failed: int


class TdxBaseDataWritePort(Protocol):
    def ingest_base_data(
        self,
        *,
        basics: list[tuple[str, str, str]],
        block_items: list[tuple[str, str, str]],
        ts: str,
        ingest_watchlists: bool,
        watchlists: list[Any],
        watchlist_sync_mode: str,
        watchlist_conflict_strategy: str,
        ingest_finance: bool,
        finance_rows: list[tuple[Any, ...]],
        finance_max_symbols: int,
        finance_rate_limit_rps: int,
        finance_fetcher: Any,
    ) -> dict[str, int]:
        ...
