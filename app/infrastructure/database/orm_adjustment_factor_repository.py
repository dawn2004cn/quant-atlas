"""ORM-based AdjustmentFactorRepository — replacement for raw-SQL version.

Uses SQLAlchemy ORM via the session factory.
"""

from __future__ import annotations

from typing import Any

from ..mappers.symbol_normalizer import SymbolNormalizer


class OrmAdjustmentFactorRepository:
    """ORM-backed adjustment factor repository (migration demo for P06)."""

    def __init__(self, session_factory):
        self._sf = session_factory

    def save_factors(
        self, stock_code: str, factors: list[dict[str, Any]]
    ) -> None:
        if not factors:
            return
        normalized = SymbolNormalizer.to_db_code(stock_code)
        session = self._sf()
        try:
            for f in factors:
                date_val = f.get("date")
                factor_val = float(f.get("factor", 1.0))
                # Upsert via raw SQL (cross-dialect)
                dialect = session.bind.dialect.name if session.bind else "sqlite"
                if dialect == "sqlite":
                    sql = """
                        INSERT INTO stock_adjustment_factor (stock_code, date, factor)
                        VALUES (?, ?, ?)
                        ON CONFLICT(stock_code, date) DO UPDATE SET factor=excluded.factor
                    """
                else:
                    sql = """
                        INSERT INTO stock_adjustment_factor (stock_code, date, factor)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE factor=VALUES(factor)
                    """
                session.execute(
                    text(sql), (normalized, date_val, factor_val)
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()

    def get_factors(
        self, stock_code: str, start_date: str = "", end_date: str = ""
    ) -> list[dict[str, Any]]:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        session = self._sf()
        try:
            params: dict[str, Any] = {"code": normalized}
            where_clauses = ["stock_code = :code"]
            if start_date:
                where_clauses.append("date >= :start")
                params["start"] = start_date[:10]
            if end_date:
                where_clauses.append("date <= :end")
                params["end"] = end_date[:10]
            sql = (
                "SELECT stock_code, date, factor FROM stock_adjustment_factor"
                " WHERE " + " AND ".join(where_clauses)
                + " ORDER BY date"
            )  # noqa: S608 — where_clauses are built from hardcoded strings, params use named parameters
            rows = session.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]
        finally:
            self._sf.remove()


from sqlalchemy import text
