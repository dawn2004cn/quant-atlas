from __future__ import annotations

"""History Repository - Single Responsibility for K-line Data."""


import logging
from typing import Any

from app.core.sql_safety import safe_sql_identifier

from ..mappers.symbol_normalizer import SymbolNormalizer
from .adapters import DatabaseAdapter

logger = logging.getLogger(__name__)
MARKET_TABLES = {
    "sh": "stock_history_sh",
    "sz": "stock_history_sz",
    "bj": "stock_history_bj",
    "hk": "stock_history_hk",
    "us": "stock_history_us",
    "btc": "stock_history_btc",
}


class HistoryRepository:
    """Repository for historical K-line data operations."""

    def __init__(self, adapter: DatabaseAdapter):
        self._adapter = adapter
        self._ph = adapter.placeholder

    def _get_table_name(self, stock_code: str) -> str:
        """Get the market-specific table name for a stock code."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        for prefix, table in MARKET_TABLES.items():
            if normalized.startswith(prefix):
                return table
        return "stock_history"

    def save_history(self, stock_code: str, history: list[dict[str, Any]]) -> None:
        """Batch save or update history."""
        if not history:
            return
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table_name = self._get_table_name(stock_code)
        rows = [
            (
                normalized,
                h.get("date") or h.get("Date"),
                h.get("open") or h.get("Open"),
                h.get("high") or h.get("High"),
                h.get("low") or h.get("Low"),
                h.get("close") or h.get("Close"),
                h.get("volume") or h.get("Volume"),
                h.get("amount") or h.get("Amount", 0),
            )
            for h in history
        ]
        ph = self._ph
        if self._ph == "?":
            sql = f"""  # noqa: S608 — table name is a safe literal, values use parameterized placeholders
                INSERT INTO {table_name} (stock_code, date, open, high, low, close, volume, amount)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
                ON CONFLICT(stock_code, date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume, amount=excluded.amount
            """
        else:
            sql = f"""  # noqa: S608 — table name is a safe literal, values use parameterized placeholders
                INSERT INTO {table_name} (stock_code, date, open, high, low, close, volume, amount)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    open=VALUES(open), high=VALUES(high), low=VALUES(low),
                    close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)
            """
        self._adapter.execute_many(sql, rows)

    def get_history(self, stock_code: str, start_date: str, end_date: str, limit: int = 10000) -> list[dict[str, Any]]:
        """Get historical data within date range."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table_name = self._get_table_name(normalized)
        s0 = str(start_date or "")[:10]
        e0 = str(end_date or "")[:10]

        ph = self._ph
        sql = f"""  # noqa: S608 — table name is a safe literal, values use parameterized placeholders
            SELECT stock_code, date, open, high, low, close, volume, amount
            FROM {table_name}
            WHERE stock_code = {ph} AND date >= {ph} AND date <= {ph}
            ORDER BY date
            LIMIT {ph}
        """
        params = (normalized, s0, e0, limit)
        return self._adapter.execute_select(sql, params)

    def get_history_latest(self, stock_code: str, limit: int = 10000) -> list[dict[str, Any]]:
        """Get latest history for a stock."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table_name = self._get_table_name(normalized)

        ph = self._ph
        sql = f"""  # noqa: S608 — table name is a safe literal, values use parameterized placeholders
            SELECT stock_code, date, open, high, low, close, volume, amount
            FROM {table_name}
            WHERE stock_code = {ph}
            ORDER BY date DESC
            LIMIT {ph}
        """
        rows = self._adapter.execute_select(sql, (normalized, limit))
        rows.reverse()
        return rows

    def get_history_bar_count(self) -> int:
        """Get total history bars count."""
        total = 0
        for table in list(MARKET_TABLES.values()) + ["stock_history"]:
            try:
                safe_table = safe_sql_identifier(table, "stock_history")
                count = self._adapter.execute_scalar(f"SELECT COUNT(*) FROM {safe_table}")
                total += count or 0
            except Exception as e:
                logger.warning("history_repository.py.get_history_bar_count: %s", e)
        return total
