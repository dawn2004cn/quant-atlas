from __future__ import annotations
"""Stock Repository - Single Responsibility for Stock CRUD."""


from datetime import datetime, timedelta
from typing import Any

from ..mappers.symbol_normalizer import SymbolNormalizer
from .adapters import DatabaseAdapter


class StockRepository:
    """Repository for stock data operations."""

    def __init__(self, adapter: DatabaseAdapter):
        self._adapter = adapter
        self._ph = adapter.placeholder

    def save_stocks(self, stocks_data: list[dict[str, Any]]) -> None:
        """Batch save or update stocks."""
        if not stocks_data:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = [
            (
                SymbolNormalizer.to_db_code(s["code"]),
                s.get("name", ""),
                float(s.get("price", 0) or 0),
                float(s.get("change_pct", 0) or 0),
                float(s.get("change_amount", 0) or 0),
                float(s.get("prev_close", 0) or 0),
                float(s.get("volume", 0) or 0),
                float(s.get("amount", 0) or 0),
                float(s.get("turnover", 0) or 0),
                float(s.get("volume_ratio", 0) or 0),
                float(s.get("amplitude", 0) or 0),
                float(s.get("pe", 0) or 0),
                float(s.get("pb", 0) or 0),
                float(s.get("total_market_cap", 0) or 0),
                str(s.get("industry", "") or ""),
                now,
            )
            for s in stocks_data
        ]

        ph = self._ph
        if self._ph == "?":
            sql = f"""
                INSERT INTO stocks (
                    code, name, price, change_pct, change_amount, prev_close,
                    volume, amount, turnover, volume_ratio, amplitude, pe, pb,
                    total_market_cap, industry, update_time
                ) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name, price=excluded.price, change_pct=excluded.change_pct,
                    change_amount=excluded.change_amount, prev_close=excluded.prev_close,
                    volume=excluded.volume, amount=excluded.amount, turnover=excluded.turnover,
                    volume_ratio=excluded.volume_ratio, amplitude=excluded.amplitude,
                    pe=excluded.pe, pb=excluded.pb, total_market_cap=excluded.total_market_cap,
                    industry=excluded.industry, update_time=excluded.update_time
            """
        else:
            sql = """
                INSERT INTO stocks (
                    code, name, price, change_pct, change_amount, prev_close,
                    volume, amount, turnover, volume_ratio, amplitude, pe, pb,
                    total_market_cap, industry, update_time
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    name=VALUES(name), price=VALUES(price), change_pct=VALUES(change_pct),
                    change_amount=VALUES(change_amount), prev_close=VALUES(prev_close),
                    volume=VALUES(volume), amount=VALUES(amount), turnover=VALUES(turnover),
                    volume_ratio=VALUES(volume_ratio), amplitude=VALUES(amplitude),
                    pe=VALUES(pe), pb=VALUES(pb), total_market_cap=VALUES(total_market_cap),
                    industry=VALUES(industry), update_time=VALUES(update_time)
            """
        self._adapter.execute_many(sql, rows)

    def get_all_stocks(self, max_age_minutes: int = 1440) -> list[dict[str, Any]]:
        """Get all stocks with optional freshness filter."""
        cutoff = (datetime.now() - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        ph = self._ph
        rows = self._adapter.execute_select(
            f"SELECT * FROM stocks WHERE update_time > {ph} ORDER BY amount DESC",
            (cutoff,),
        )
        if not rows:
            rows = self._adapter.execute_select("SELECT * FROM stocks ORDER BY update_time DESC")
        return self._normalize_codes(rows)

    def list_all_codes(self) -> list[str]:
        """List all stock codes."""
        rows = self._adapter.execute_select("SELECT code FROM stocks ORDER BY amount DESC")
        return [r["code"] for r in rows]

    def get_stocks_by_codes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Get stocks by codes."""
        if not codes:
            return []
        normalized_codes = [SymbolNormalizer.to_db_code(c) for c in codes]
        ph = self._ph
        placeholders = ",".join([ph] * len(normalized_codes))
        sql = f"SELECT * FROM stocks WHERE code IN ({placeholders})"
        rows = self._adapter.execute_select(sql, tuple(normalized_codes))
        return self._normalize_codes(rows)

    def list_stocks_for_admin(self, limit: int = 8000) -> list[dict[str, Any]]:
        """List stocks for admin with limit."""
        ph = self._ph
        rows = self._adapter.execute_select(
            f"SELECT * FROM stocks ORDER BY update_time DESC LIMIT {ph}",
            (limit,),
        )
        return self._normalize_codes(rows)

    def get_stock_count(self) -> int:
        """Get total stock count."""
        return self._adapter.execute_scalar("SELECT COUNT(*) FROM stocks") or 0

    def _normalize_codes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize stock codes in rows."""
        result = []
        for r in rows:
            if "update_time" in r and isinstance(r["update_time"], datetime):
                r["update_time"] = r["update_time"].strftime("%Y-%m-%d %H:%M:%S")
            result.append(r)
        return result