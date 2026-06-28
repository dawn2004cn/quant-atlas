"""ORM-based HistoryRepository — replacement for raw-SQL HistoryRepository.

Uses SQLAlchemy ORM via the session factory from ``app.infrastructure.database.orm``.
Supports multi-table history storage per market.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, text

from ..mappers.symbol_normalizer import SymbolNormalizer
from ..models.market import StockHistory

logger = logging.getLogger(__name__)

MARKET_TABLES = {
    "sh": "stock_history_sh",
    "sz": "stock_history_sz",
    "bj": "stock_history_bj",
    "hk": "stock_history_hk",
    "us": "stock_history_us",
    "btc": "stock_history_btc",
}


class OrmHistoryRepository:
    """ORM-backed history repository (migration demo for P06)."""

    def __init__(self, session_factory):
        self._sf = session_factory

    # ── Public interface (identical to raw-SQL HistoryRepository) ────

    def _get_table_name(self, stock_code: str) -> str:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        for prefix, table in MARKET_TABLES.items():
            if normalized.startswith(prefix):
                return table
        return "stock_history"

    def save_history(
        self, stock_code: str, history: list[dict[str, Any]]
    ) -> None:
        if not history:
            return
        normalized = SymbolNormalizer.to_db_code(stock_code)
        session = self._sf()
        try:
            for h in history:
                date_val = h.get("date") or h.get("Date")
                if not date_val:
                    continue
                obj = session.get(StockHistory, (normalized, str(date_val)))
                if obj is None:
                    obj = StockHistory(stock_code=normalized, date=str(date_val))
                    session.add(obj)
                obj.open = float(h.get("open") or h.get("Open", 0))
                obj.high = float(h.get("high") or h.get("High", 0))
                obj.low = float(h.get("low") or h.get("Low", 0))
                obj.close = float(h.get("close") or h.get("Close", 0))
                obj.volume = float(h.get("volume") or h.get("Volume", 0))
                obj.amount = float(
                    h.get("amount") or h.get("Amount", 0)
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()

    def get_history(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        s0 = str(start_date or "")[:10]
        e0 = str(end_date or "")[:10]
        session = self._sf()
        try:
            rows = (
                session.execute(
                    select(StockHistory)
                    .where(
                        StockHistory.stock_code == normalized,
                        StockHistory.date >= s0,
                        StockHistory.date <= e0,
                    )
                    .order_by(StockHistory.date)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._sf.remove()

    def get_history_latest(
        self, stock_code: str, limit: int = 10000
    ) -> list[dict[str, Any]]:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        session = self._sf()
        try:
            rows = (
                session.execute(
                    select(StockHistory)
                    .where(StockHistory.stock_code == normalized)
                    .order_by(StockHistory.date.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            rows.reverse()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._sf.remove()

    def get_history_bar_count(self) -> int:
        total = 0
        session = self._sf()
        try:
            for table in list(MARKET_TABLES.values()) + ["stock_history"]:
                try:
                    count = session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()
                    total += count or 0
                except Exception as e:
                    logger.warning(
                        "orm_history_repository.get_history_bar_count: %s", e
                    )
            return total
        finally:
            self._sf.remove()

    @staticmethod
    def _row_to_dict(row: StockHistory) -> dict[str, Any]:
        return {
            "stock_code": row.stock_code,
            "date": row.date,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
            "amount": row.amount,
        }
