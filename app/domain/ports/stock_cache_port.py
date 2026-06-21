from __future__ import annotations
"""Port for local quote/history cache (stock_cache.db / MySQL adapter)."""

from typing import Any, Protocol


class StockCachePort(Protocol):
    """Application-facing stock cache contract (implemented by ``StockCache``)."""

    def get_all_stocks(self, max_age_minutes: int = 1440) -> list[dict[str, Any]]:
        ...

    def get_stocks_by_codes(self, codes: list[str]) -> list[dict[str, Any]]:
        ...

    def get_stock_history_for_code(self, code: str, limit: int = 5000) -> list[dict[str, Any]]:
        ...

    def list_stocks_for_admin(self, limit: int = 8000) -> list[dict[str, Any]]:
        ...

    def stock_cache_admin_stats(self) -> dict[str, Any]:
        ...

    def save_sentiment(self, market: str, up_count: int, down_count: int, flat_count: int) -> None:
        ...

    def save_sentiment_daily(
        self,
        market: str,
        trade_date: str,
        up_count: int,
        down_count: int,
        flat_count: int,
    ) -> None:
        ...

    def get_latest_sentiment(self, market: str) -> dict[str, Any] | None:
        ...
