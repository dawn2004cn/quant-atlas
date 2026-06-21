"""ORM-based StockRepository — replacement for raw-SQL StockRepository.

Uses SQLAlchemy ORM via the session factory from ``app.infrastructure.database.orm``.
Implements the same public interface as the original raw-SQL version so callers
need zero changes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func

from ..mappers.symbol_normalizer import SymbolNormalizer
from ..models.market import Stock
from ..orm import Base, create_session_factory


class OrmStockRepository:
    """ORM-backed stock repository (migration demo for P06)."""

    def __init__(self, session_factory):
        self._sf = session_factory

    # ── Public interface (identical to raw-SQL StockRepository) ──────

    def save_stocks(self, stocks_data: list[dict[str, Any]]) -> None:
        if not stocks_data:
            return
        now = datetime.now()
        session = self._sf()
        try:
            for s in stocks_data:
                code = SymbolNormalizer.to_db_code(s["code"])
                obj = session.get(Stock, code)
                if obj is None:
                    obj = Stock(code=code)
                    session.add(obj)
                obj.name = s.get("name", "")
                obj.price = float(s.get("price", 0) or 0)
                obj.change_pct = float(s.get("change_pct", 0) or 0)
                obj.change_amount = float(s.get("change_amount", 0) or 0)
                obj.prev_close = float(s.get("prev_close", 0) or 0)
                obj.volume = float(s.get("volume", 0) or 0)
                obj.amount = float(s.get("amount", 0) or 0)
                obj.turnover = float(s.get("turnover", 0) or 0)
                obj.volume_ratio = float(s.get("volume_ratio", 0) or 0)
                obj.amplitude = float(s.get("amplitude", 0) or 0)
                obj.pe = float(s.get("pe", 0) or 0)
                obj.pb = float(s.get("pb", 0) or 0)
                obj.total_market_cap = float(s.get("total_market_cap", 0) or 0)
                obj.industry = str(s.get("industry", "") or "")
                obj.update_time = now
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()

    def get_all_stocks(
        self, max_age_minutes: int = 1440
    ) -> list[dict[str, Any]]:
        session = self._sf()
        try:
            cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
            stmt = (
                select(Stock)
                .where(Stock.update_time > cutoff)
                .order_by(Stock.amount.desc())
            )
            rows = list(session.execute(stmt).scalars().all())
            if not rows:
                rows = (
                    session.execute(
                        select(Stock).order_by(Stock.update_time.desc())
                    )
                    .scalars()
                    .all()
                )
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._sf.remove()

    def list_all_codes(self) -> list[str]:
        session = self._sf()
        try:
            rows = (
                session.execute(
                    select(Stock.code).order_by(Stock.amount.desc())
                )
                .scalars()
                .all()
            )
            return list(rows)
        finally:
            self._sf.remove()

    def get_stocks_by_codes(
        self, codes: list[str]
    ) -> list[dict[str, Any]]:
        if not codes:
            return []
        normalized = [SymbolNormalizer.to_db_code(c) for c in codes]
        session = self._sf()
        try:
            rows = (
                session.execute(
                    select(Stock).where(Stock.code.in_(normalized))
                )
                .scalars()
                .all()
            )
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._sf.remove()

    def list_stocks_for_admin(
        self, limit: int = 8000
    ) -> list[dict[str, Any]]:
        session = self._sf()
        try:
            rows = (
                session.execute(
                    select(Stock)
                    .order_by(Stock.update_time.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._sf.remove()

    def get_stock_count(self) -> int:
        session = self._sf()
        try:
            return (
                session.execute(select(func.count(Stock.code))).scalar() or 0
            )
        finally:
            self._sf.remove()

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: Stock) -> dict[str, Any]:
        d = {
            "code": row.code,
            "name": row.name,
            "price": row.price,
            "change_pct": row.change_pct,
            "change_amount": row.change_amount,
            "prev_close": row.prev_close,
            "volume": row.volume,
            "amount": row.amount,
            "turnover": row.turnover,
            "volume_ratio": row.volume_ratio,
            "amplitude": row.amplitude,
            "pe": row.pe,
            "pb": row.pb,
            "total_market_cap": row.total_market_cap,
            "industry": row.industry,
        }
        if row.update_time:
            d["update_time"] = row.update_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return d
