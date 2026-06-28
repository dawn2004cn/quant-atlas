from __future__ import annotations

import logging
import os
import re
import time
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


def _assert_ddl_reset_allowed(operation: str) -> None:
    allowed = os.getenv("ALLOW_HISTORY_TRUNCATE", "").lower()
    if allowed not in {"1", "true", "yes", "on"}:
        raise RuntimeError(f"ddl_reset_requires_explicit_flag:{operation}")


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





def _mysql_write_chunk() -> int:

    return max(50, min(get_runtime_int("TDX_MYSQL_WRITE_CHUNK", 400), 5000))


def _commit_per_chunk() -> bool:

    return get_runtime_bool("TDX_MYSQL_COMMIT_PER_CHUNK", True)


def _is_retryable_mysql_error(exc: BaseException) -> bool:

    if isinstance(exc, pymysql.err.OperationalError) and exc.args:
        code = int(exc.args[0])
        if code in (1205, 2013, 2006):
            return True
    msg = str(exc)
    return (
        "Lock wait timeout exceeded" in msg
        or "Lost connection to MySQL server" in msg
        or "MySQL server has gone away" in msg
    )





class MySQLTdxDaykSyncSession:

    """Reuse one MySQL connection across a TDX day-K sync run."""



    def __init__(

        self,

        conn_port: MySQLConnectionAdapter,

        *,

        table_suffix: str = "",

        insert_only: bool = False,

    ) -> None:

        self._conn_port = conn_port

        self._table_suffix = _validate_table_suffix(table_suffix)

        self._insert_only = insert_only

        self._conn = conn_port.connect_sync()

        self._cur = self._conn.cursor()

    def _acquire_mysql_lock(self, name: str, timeout: int = 10) -> Any:
        conn = self._conn_port.connect(autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT GET_LOCK(%s, %s)", (name, timeout))
                row = cur.fetchone()
            if _mysql_lock_value(row) != 1:
                self._conn_port.close(conn)
                raise RuntimeError(f"mysql_lock_not_acquired:{name}")
            self._conn_port.commit(conn)
            return conn
        except Exception:
            try:
                self._conn_port.rollback(conn)
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
            try:
                self._conn_port.close(conn)
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
            raise

    def _release_mysql_lock(self, conn: Any, name: str) -> None:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT RELEASE_LOCK(%s)", (name,))
            self._conn_port.commit(conn)
        finally:
            self._conn_port.close(conn)



    def batch_get_latest_dates(self, stock_codes: list[str]) -> dict[str, str | None]:

        if not stock_codes:

            return {SymbolNormalizer.to_db_code(c): None for c in stock_codes}



        sh_codes = [c for c in stock_codes if c.lower().startswith("sh")]

        sz_codes = [c for c in stock_codes if c.lower().startswith("sz")]

        bj_codes = [c for c in stock_codes if c.lower().startswith("bj")]



        result: dict[str, str | None] = {

            SymbolNormalizer.to_db_code(c): None for c in stock_codes

        }



        for codes, prefix in [

            (sh_codes, "sh"),

            (sz_codes, "sz"),

            (bj_codes, "bj"),

        ]:

            if not codes:

                continue

            table = _table_for_code(f"{prefix}000000", suffix=self._table_suffix)

            db_codes = [SymbolNormalizer.to_db_code(c) for c in codes]

            placeholders = ",".join(["%s"] * len(db_codes))

            sql = f"""

                SELECT stock_code, MAX(date) as max_date

                FROM {table}

                WHERE stock_code IN ({placeholders})

                GROUP BY stock_code

            """

            try:

                self._cur.execute(sql, db_codes)

                for row in self._cur.fetchall():

                    code, max_date = row

                    result[code] = str(max_date) if max_date else None

            except Exception as exc:

                logger.warning("batch latest dates failed (%s): %s", table, exc)

        return result



    def _bars_sql(self, table: str) -> str:

        if self._insert_only:

            return f"""

                INSERT INTO {table}

                    (stock_code, date, open, high, low, close, volume, amount)

                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)

            """

        return f"""

            INSERT INTO {table} (stock_code, date, open, high, low, close, volume, amount)

            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)

            ON DUPLICATE KEY UPDATE

                open=VALUES(open), high=VALUES(high), low=VALUES(low),

                close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)

        """



    def _reconnect(self) -> None:

        try:

            self._cur.close()

        except Exception:

            logger.warning("Suppressed exception", exc_info=True)
            pass

        try:

            self._conn.close()

        except Exception:

            logger.warning("Suppressed exception", exc_info=True)
            pass

        self._conn = self._conn_port.connect_sync()

        self._cur = self._conn.cursor()



    def _executemany_with_retry(self, sql: str, batch: list[tuple[Any, ...]]) -> None:

        max_retries = max(1, get_runtime_int("TDX_MYSQL_WRITE_RETRIES", 4))

        retry_delay = max(1, get_runtime_int("TDX_MYSQL_WRITE_RETRY_SEC", 8))

        for attempt in range(max_retries):

            try:

                self._cur.executemany(sql, batch)

                return

            except Exception as exc:

                if _is_retryable_mysql_error(exc) and attempt < max_retries - 1:

                    logger.warning(

                        "MySQL write retry %s/%s: %s",

                        attempt + 1,

                        max_retries,

                        exc,

                    )

                    time.sleep(retry_delay)

                    self._reconnect()

                    continue

                raise



    def write_bars(self, stock_code: str, rows: list[dict[str, Any]]) -> int:

        if not rows:

            return 0

        normalized = SymbolNormalizer.to_db_code(stock_code)

        table = _table_for_code(normalized, suffix=self._table_suffix)

        sql = self._bars_sql(table)

        batch = [

            (

                normalized,

                h.get("date"),

                float(h.get("open", 0) or 0),

                float(h.get("high", 0) or 0),

                float(h.get("low", 0) or 0),

                float(h.get("close", 0) or 0),

                float(h.get("volume", 0) or 0),

                float(h.get("amount", 0) or 0),

            )

            for h in rows

        ]

        chunk = _mysql_write_chunk()

        written = 0

        for i in range(0, len(batch), chunk):

            part = batch[i : i + chunk]

            self._executemany_with_retry(sql, part)

            written += len(part)

            if _commit_per_chunk() or self._insert_only:

                self._conn_port.commit(self._conn)

        return written



    def write_factors(self, stock_code: str, factors: list[dict[str, Any]]) -> int:

        if not factors:

            return 0

        normalized = SymbolNormalizer.to_db_code(stock_code)

        sql = """

            INSERT INTO stock_adjustment_factor (stock_code, date, factor)

            VALUES (%s,%s,%s)

            ON DUPLICATE KEY UPDATE factor=VALUES(factor)

        """

        batch = [

            (normalized, f.get("date"), float(f.get("factor", 1.0)))

            for f in factors

        ]

        chunk = _mysql_write_chunk()

        written = 0

        for i in range(0, len(batch), chunk):

            part = batch[i : i + chunk]

            self._executemany_with_retry(sql, part)

            written += len(part)

            if _commit_per_chunk():

                self._conn_port.commit(self._conn)

        return written



    def commit(self) -> None:

        self._conn_port.commit(self._conn)



    def rollback(self) -> None:

        self._conn.rollback()



    def close(self) -> None:

        try:

            self._cur.close()

        finally:

            self._conn.close()





class MySQLTdxDaykRepository:

    _HISTORY_TABLES = frozenset(_HISTORY_BASE_TABLES + tuple(f"{t}_new" for t in _HISTORY_BASE_TABLES))



    def __init__(self, mysql: MysqlSettings) -> None:

        self._conn_port = MySQLConnectionAdapter(mysql)

    def _acquire_mysql_lock(self, name: str, timeout: int = 10) -> Any:
        return _acquire_mysql_lock(self._conn_port, name, timeout=timeout)

    def _release_mysql_lock(self, conn: Any, name: str) -> None:
        _release_mysql_lock(self._conn_port, conn, name)



    def open_sync_session(

        self,

        *,

        table_suffix: str = "",

        insert_only: bool = False,

    ) -> MySQLTdxDaykSyncSession:

        return MySQLTdxDaykSyncSession(

            self._conn_port,

            table_suffix=table_suffix,

            insert_only=insert_only,

        )



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



    def truncate_adjustment_factors(self) -> None:
        """全量重灌前清空复权因子（维护窗口，直连 MySQL 绕过连接池）。"""
        _assert_ddl_reset_allowed("truncate_adjustment_factors")
        lock_conn = self._acquire_mysql_lock("quant_atlas_tdx_adjustment_factor")
        try:
            from app.infrastructure.database.mysql_client import mysql_admin_execute

            mysql_admin_execute(self._conn_port._mysql, "TRUNCATE TABLE stock_adjustment_factor")
            logger.info("TRUNCATED stock_adjustment_factor")
        finally:
            self._release_mysql_lock(lock_conn, "quant_atlas_tdx_adjustment_factor")

    def truncate_history_tables(self, table_suffix: str = "") -> None:
        """清空日 K 分表（如 ``stock_history_sh_new``）。"""
        _assert_ddl_reset_allowed("truncate_history_tables")
        suffix = _validate_table_suffix(table_suffix)
        lock_name = "quant_atlas_tdx_truncate_history"
        lock_conn = self._acquire_mysql_lock(lock_name)
        try:
            from app.infrastructure.database.mysql_client import mysql_admin_execute

            for base in _HISTORY_BASE_TABLES:
                mysql_admin_execute(self._conn_port._mysql, f"TRUNCATE TABLE {base}{suffix}")
            logger.info("TRUNCATED history tables suffix=%r", suffix)
        finally:
            self._release_mysql_lock(lock_conn, lock_name)

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



    @staticmethod

    def swap_reload_tables(table_suffix: str = "_new") -> None:

        """原子切换：``stock_history_*{suffix}`` → 生产表，旧表改名为 ``*_old``。"""

        suffix = _validate_table_suffix(table_suffix)

        if not suffix:

            raise ValueError("swap_reload_tables requires a non-empty suffix (e.g. _new)")

        _assert_ddl_reset_allowed("swap_reload_tables")

        renames = []

        for base in _HISTORY_BASE_TABLES:

            renames.append(f"{base} TO {base}_old")

            renames.append(f"{base}{suffix} TO {base}")

        sql = "RENAME TABLE " + ", ".join(renames)

        conn_port = None
        lock_conn = None

        from app.config import get_settings



        settings = get_settings()

        if not settings.mysql:

            raise ValueError("mysql_not_configured")

        conn_port = MySQLConnectionAdapter(settings.mysql)

        conn = conn_port.connect()

        try:

            lock_name = "quant_atlas_tdx_swap_history"
            lock_conn = _acquire_mysql_lock(conn_port, lock_name)

            with conn.cursor() as cur:

                cur.execute(sql)

            conn_port.commit(conn)

            logger.info("MySQL history tables swapped: suffix=%s", suffix)

        except Exception:

            conn_port.rollback(conn)

            raise

        finally:

            if lock_conn is not None:
                _release_mysql_lock(conn_port, lock_conn, lock_name)
            conn.close()


