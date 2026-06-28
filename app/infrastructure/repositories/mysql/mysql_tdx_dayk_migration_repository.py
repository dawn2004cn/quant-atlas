from __future__ import annotations


import logging
import os

from typing import Any


from app.core.utils.sql_utils import validate_identifier

from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter

from app.infrastructure.database.mysql_settings import MysqlSettings

from app.config import get_settings


logger = logging.getLogger(__name__)


_HISTORY_BASE_TABLES = ("stock_history_sh", "stock_history_sz", "stock_history_bj")

_ALLOWED_SUFFIXES = frozenset({"", "_new"})

_SUFFIX_RE = __import__("re").compile(r"^_[a-z0-9_]{0,31}$")


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


class MySQLTdxDaykMigrationRepository:
    """Schema migration repository for TDX day-K data."""

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def _acquire_mysql_lock(self, name: str, timeout: int = 10) -> Any:
        return _acquire_mysql_lock(self._conn_port, name, timeout=timeout)

    def _release_mysql_lock(self, conn: Any, name: str) -> None:
        _release_mysql_lock(self._conn_port, conn, name)

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