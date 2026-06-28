from __future__ import annotations


import logging
import re

from typing import Any

import pymysql
import pymysql.err


from app.core.runtime_config import get_runtime_bool, get_runtime_int

from app.core.utils.sql_utils import validate_identifier
from app.domain.shared.symbol_normalizer import SymbolNormalizer

from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter

from app.infrastructure.database.mysql_settings import MysqlSettings


logger = logging.getLogger(__name__)


_HISTORY_BASE_TABLES = ("stock_history_sh", "stock_history_sz", "stock_history_bj")

_ALLOWED_SUFFIXES = frozenset({"", "_new"})

_SUFFIX_RE = re.compile(r"^_[a-z0-9_]{0,31}$")


def _mysql_lock_value(row: Any) -> int:
    if isinstance(row, dict):
        return int(next(iter(row.values())))
    if isinstance(row, (int, float)):
        return int(row)
    return int(row[0])


def _acquire_mysql_lock(conn_port: Any, name: str, timeout: int = 10) -> Any:
    conn = conn_port.connect(autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT GET_LOCK(%s, %s)", (name, timeout))
            row = cur.fetchone()
        if _mysql_lock_value(row) != 1:
            conn_port.close(conn)
            raise RuntimeError(f"mysql_lock_not_acquired:{name}")
        conn_port.commit(conn)
        return conn
    except Exception:
        try:
            conn_port.rollback(conn)
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        try:
            conn_port.close(conn)
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        raise


def _release_mysql_lock(conn_port: Any, conn: Any, name: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT RELEASE_LOCK(%s)", (name,))
        conn_port.commit(conn)
    finally:
        conn_port.close(conn)


def _validate_table_suffix(suffix: str) -> str:

    if suffix not in _ALLOWED_SUFFIXES and not (suffix and _SUFFIX_RE.match(suffix)):

        raise ValueError(f"unsupported MySQL history table suffix: {suffix!r}")

    return suffix


def _table_for_code(stock_code: str, *, suffix: str = "") -> str:

    suffix = _validate_table_suffix(suffix)

    if stock_code.startswith("sh"):

        base = "stock_history_sh"

    elif stock_code.startswith("sz"):

        base = "stock_history_sz"

    elif stock_code.startswith("bj"):

        base = "stock_history_bj"

    else:

        base = "stock_history"
    return f"{base}{suffix}"


class MySQLTdxDaykReadRepository:
    """Read-only repository for TDX day-K data."""

    _HISTORY_TABLES = frozenset(_HISTORY_BASE_TABLES + tuple(f"{t}_new" for t in _HISTORY_BASE_TABLES))

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def _acquire_mysql_lock(self, name: str, timeout: int = 10) -> Any:
        return _acquire_mysql_lock(self._conn_port, name, timeout=timeout)

    def _release_mysql_lock(self, conn: Any, name: str) -> None:
        _release_mysql_lock(self._conn_port, conn, name)

    def list_history_calendar_dates(self, *, table_suffix: str = "") -> list[str]:
        suffix = _validate_table_suffix(table_suffix)

        conn = self._conn_port.connect()
        try:
            all_dates: set[str] = set()
            with conn.cursor() as cur:
                # 分别查询每个表的日期，避免UNION查询在大表上超时
                for tbl in [f"stock_history_sh{suffix}", f"stock_history_sz{suffix}", f"stock_history_bj{suffix}"]:
                    if not validate_identifier(tbl):
                        logger.warning("Skipping invalid table name: %s", tbl)
                        continue
                    try:
                        safe_tbl = f"`{tbl}`"
                        cur.execute(f"SELECT DISTINCT date FROM {safe_tbl}")
                        for row in cur.fetchall():
                            if row[0]:
                                all_dates.add(str(row[0]))
                    except Exception:
                        logger.warning("Suppressed exception", exc_info=True)

            return sorted(all_dates)

        finally:
            conn.close()

    def list_history_stock_codes(self, *, limit: int | None = None) -> list[str]:
        conn = self._conn_port.connect()
        try:
            all_codes: set[str] = set()
            with conn.cursor() as cur:
                for tbl in ["stock_history_sh", "stock_history_sz", "stock_history_bj"]:
                    if not validate_identifier(tbl):
                        logger.warning("Skipping invalid table name: %s", tbl)
                        continue
                    safe_tbl = f"`{tbl}`"
                    try:
                        if limit is not None:
                            safe_limit = int(limit)
                            if safe_limit < 0:
                                safe_limit = 0
                            cur.execute(f"SELECT DISTINCT stock_code FROM {safe_tbl} LIMIT {safe_limit}")
                        else:
                            cur.execute(f"SELECT DISTINCT stock_code FROM {safe_tbl}")
                        for row in cur.fetchall():
                            if row[0]:
                                all_codes.add(str(row[0]))
                        if limit is not None and len(all_codes) >= limit:
                            break
                    except Exception:
                        logger.warning("Suppressed exception", exc_info=True)
                        pass  # 表不存在或其他错误时跳过

            result = sorted(all_codes)
            if limit is not None:
                result = result[:limit]
            return result

        finally:
            conn.close()

    def fetch_history_rows(self, table: str, codes: list[str]) -> list[dict[str, Any]]:
        if table not in self._HISTORY_TABLES or not codes or not validate_identifier(table):
            return []

        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(codes))
                sql = (
                    f"SELECT stock_code, date, open, high, low, close, volume, amount "
                    f"FROM {table} WHERE stock_code IN ({placeholders}) "
                    f"ORDER BY stock_code, date ASC"
                )
                cur.execute(sql, codes)
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def fetch_history_rows_for_code(
        self,
        stock_code: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = _table_for_code(normalized)
        if not table.startswith("stock_history") or not validate_identifier(table):
            return []

        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                sql = (
                    f"SELECT stock_code, date, open, high, low, close, volume, amount "
                    f"FROM {table} WHERE stock_code = %s"
                )
                params: list[Any] = [normalized]
                if start_date:
                    sql += " AND date >= %s"
                    params.append(str(start_date)[:10])
                if end_date:
                    sql += " AND date <= %s"
                    params.append(str(end_date)[:10])
                sql += " ORDER BY date ASC"
                cur.execute(sql, params)
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def list_stock_codes_updated_since(
        self,
        since_date: str,
        *,
        limit: int | None = None,
    ) -> list[str]:
        since = str(since_date or "")[:10]
        if not since:
            return self.list_history_stock_codes(limit=limit)

        conn = self._conn_port.connect()
        codes: set[str] = set()
        try:
            with conn.cursor() as cur:
                for table in sorted(self._HISTORY_TABLES):
                    cur.execute(
                        f"SELECT DISTINCT stock_code FROM {table} WHERE date >= %s",
                        (since,),
                    )
                    for row in cur.fetchall():
                        if row and row[0]:
                            codes.add(str(row[0]))
        finally:
            conn.close()
        out = sorted(codes)
        if limit is not None:
            return out[: max(0, int(limit))]
        return out

    def fetch_factors_for_code(self, stock_code: str) -> list[dict[str, Any]]:
        """读取单只股票的前复权因子."""
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, factor FROM stock_adjustment_factor WHERE stock_code=%s ORDER BY date ASC",
                    (stock_code,),
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()