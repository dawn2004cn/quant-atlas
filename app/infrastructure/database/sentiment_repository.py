from __future__ import annotations

"""Sentiment Repository - Single Responsibility for Market Sentiment Data."""


from datetime import datetime
from typing import Any

from .adapters import DatabaseAdapter


class SentimentRepository:
    """Repository for market sentiment data operations."""

    def __init__(self, adapter: DatabaseAdapter):
        self._adapter = adapter
        self._ph = adapter.placeholder

    def save_sentiment(self, market: str, up_count: int, down_count: int, flat_count: int) -> None:
        """Save market sentiment."""
        total = int(up_count) + int(down_count) + int(flat_count)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self._ph == "?":
            sql = """
                INSERT INTO market_sentiment (market, up_count, down_count, flat_count, total_count, update_time)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(market) DO UPDATE SET
                    up_count=excluded.up_count, down_count=excluded.down_count,
                    flat_count=excluded.flat_count, total_count=excluded.total_count, update_time=excluded.update_time
            """
        else:
            sql = """
                INSERT INTO market_sentiment (market, up_count, down_count, flat_count, total_count, update_time)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    up_count=VALUES(up_count), down_count=VALUES(down_count),
                    flat_count=VALUES(flat_count), total_count=VALUES(total_count), update_time=VALUES(update_time)
            """
        self._adapter.execute_many(sql, [(market, int(up_count), int(down_count), int(flat_count), total, now)])

    def save_sentiment_daily(self, market: str, trade_date: str, up_count: int, down_count: int, flat_count: int) -> None:
        """Save daily market sentiment."""
        total = int(up_count) + int(down_count) + int(flat_count)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        td = str(trade_date or "")[:10]
        if self._ph == "?":
            sql = """
                INSERT INTO market_sentiment_daily (market, trade_date, up_count, down_count, flat_count, total_count, update_time)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(market, trade_date) DO UPDATE SET
                    up_count=excluded.up_count, down_count=excluded.down_count,
                    flat_count=excluded.flat_count, total_count=excluded.total_count, update_time=excluded.update_time
            """
        else:
            sql = """
                INSERT INTO market_sentiment_daily (market, trade_date, up_count, down_count, flat_count, total_count, update_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    up_count=VALUES(up_count), down_count=VALUES(down_count),
                    flat_count=VALUES(flat_count), total_count=VALUES(total_count), update_time=VALUES(update_time)
            """
        self._adapter.execute_many(sql, [(market, td, int(up_count), int(down_count), int(flat_count), total, now)])

    def get_latest_sentiment(self, market: str) -> dict[str, Any] | None:
        """Get latest sentiment for a market."""
        ph = self._ph
        rows = self._adapter.execute_select(
            f"SELECT * FROM market_sentiment WHERE market = {ph} LIMIT 1",  # noqa: S608 — table hardcoded, values use parameterized placeholder
            (market,),
        )
        return rows[0] if rows else None

    def get_sentiment_for_trade_date(self, market: str, trade_date: str) -> dict[str, Any] | None:
        """Get sentiment for a specific trade date."""
        td = str(trade_date or "")[:10]
        ph = self._ph
        rows = self._adapter.execute_select(
            f"SELECT * FROM market_sentiment_daily WHERE market = {ph} AND trade_date = {ph} LIMIT 1",  # noqa: S608 — table hardcoded, values use parameterized placeholder
            (market, td),
        )
        return rows[0] if rows else None
