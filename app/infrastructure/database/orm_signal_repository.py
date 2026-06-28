"""ORM-based SignalRepository (migration demo for P06).

Wraps the existing signal_flag_pool table via SQLAlchemy ORM.
Supports the same public interface as the raw-SQL signal repository.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text


class OrmSignalRepository:
    """ORM-backed signal flag pool repository (migration demo for P06)."""

    def __init__(self, session_factory):
        self._sf = session_factory

    def save_signal(self, signal: dict[str, Any]) -> int:
        session = self._sf()
        try:
            cols = ", ".join(signal.keys())
            ph = ", ".join([f":{k}" for k in signal])
            sql = f"INSERT INTO signal_flag_pool ({cols}) VALUES ({ph})"
            result = session.execute(text(sql), signal)
            session.commit()
            return result.lastrowid or 0
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()

    def get_signal(self, signal_id: int) -> dict[str, Any] | None:
        session = self._sf()
        try:
            row = (
                session.execute(
                    text(
                        "SELECT * FROM signal_flag_pool WHERE id = :id"
                    ),
                    {"id": signal_id},
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None
        finally:
            self._sf.remove()

    def list_signals(
        self,
        symbol: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        session = self._sf()
        try:
            where_clauses = []
            params: dict[str, Any] = {}
            if symbol:
                where_clauses.append("symbol = :symbol")
                params["symbol"] = symbol
            if status:
                where_clauses.append("status = :status")
                params["status"] = status
            where_sql = (
                " WHERE " + " AND ".join(where_clauses)
                if where_clauses
                else ""
            )
            rows = (
                session.execute(
                    text(
                        f"SELECT * FROM signal_flag_pool{where_sql}"
                        f" ORDER BY created_at DESC LIMIT :lim OFFSET :off"
                    ),
                    {**params, "lim": limit, "off": offset},
                )
                .mappings()
                .all()
            )
            return [dict(r) for r in rows]
        finally:
            self._sf.remove()

    def count_signals(
        self, symbol: str | None = None, status: str | None = None
    ) -> int:
        session = self._sf()
        try:
            where_clauses = []
            params: dict[str, Any] = {}
            if symbol:
                where_clauses.append("symbol = :symbol")
                params["symbol"] = symbol
            if status:
                where_clauses.append("status = :status")
                params["status"] = status
            where_sql = (
                " WHERE " + " AND ".join(where_clauses)
                if where_clauses
                else ""
            )
            return (
                session.execute(
                    text(
                        f"SELECT COUNT(*) FROM signal_flag_pool{where_sql}"
                    ),
                    params,
                ).scalar()
                or 0
            )
        finally:
            self._sf.remove()

    def update_status(
        self, signal_id: int, status: str
    ) -> bool:
        session = self._sf()
        try:
            result = session.execute(
                text(
                    "UPDATE signal_flag_pool SET status = :status WHERE id = :id"
                ),
                {"status": status, "id": signal_id},
            )
            session.commit()
            return result.rowcount > 0
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()
