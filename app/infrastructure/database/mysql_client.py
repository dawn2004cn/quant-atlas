from __future__ import annotations

"""MySQL access helpers backed by SQLAlchemy connection pooling.

This module provides pooled DBAPI connections while maintaining backward
compatibility for legacy thread-local connection management.
"""


import threading
from typing import Any

import pymysql
import pymysql.err
from pymysql.cursors import DictCursor
from sqlalchemy.exc import OperationalError as SAOperationalError

from app.core.logger import get_logger

from .mysql_settings import MysqlSettings
from .orm import create_db_engine, mysql_database_uri, mysql_engine_kwargs


def _mysql_ssl_args() -> dict:
    """Return pymysql SSL dict if MYSQL_SSL_* env variables are set."""
    import os
    ca = os.getenv("MYSQL_SSL_CA", "").strip()
    cert = os.getenv("MYSQL_SSL_CERT", "").strip()
    key = os.getenv("MYSQL_SSL_KEY", "").strip()
    if ca or cert or key:
        ssl_args: dict[str, str] = {}
        if ca:
            ssl_args["ca"] = ca
        if cert:
            ssl_args["cert"] = cert
        if key:
            ssl_args["key"] = key
        return {"ssl": ssl_args}
    return {}

logger = get_logger(__name__)

# Thread-local storage for legacy "pinned" connections
_tls = threading.local()


def _unwrap_mysql_error_code(exc: BaseException) -> int | None:
    if isinstance(exc, pymysql.err.OperationalError):
        return int(exc.args[0]) if exc.args else None
    if isinstance(exc, SAOperationalError):
        orig = getattr(exc, "orig", None)
        if isinstance(orig, pymysql.err.OperationalError):
            return int(orig.args[0]) if orig.args else None
    return None


def _ensure_database_exists(ms: MysqlSettings) -> None:
    srv = None
    try:
        srv = pymysql.connect(
            host=ms.host,
            port=ms.port,
            user=ms.user,
            password=ms.password,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=10,
            read_timeout=60,
            write_timeout=60,
        **_mysql_ssl_args()
)
        with srv.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{ms.database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        srv.commit()
    except Exception:
        if srv:
            srv.rollback()
        raise
    finally:
        if srv:
            srv.close()


def _get_pooled_conn(ms: MysqlSettings, *, autocommit: bool = False):
    """Get a raw connection from the SQLAlchemy pool."""
    uri = mysql_database_uri(ms)
    # create_db_engine handles caching internally
    eng = create_db_engine(uri, **mysql_engine_kwargs())
    try:
        conn = eng.raw_connection()
    except Exception as exc:
        code = _unwrap_mysql_error_code(exc)
        if code == 1049:
            _ensure_database_exists(ms)
            # 数据库创建后，使用相同的URI再次获取引擎，应该会返回缓存中的实例
            conn = eng.raw_connection()
        else:
            raise

    try:
        # DBAPI connection wrapped in fairy
        conn.connection.autocommit(bool(autocommit))
    except (AttributeError, Exception) as e:
        logger.warning("mysql_client.py._get_pooled_conn: %s", e)
    return conn


def mysql_get_connection(ms: MysqlSettings, *, autocommit: bool = False):
    """Get a pooled DBAPI connection. Caller MUST call .close() to return to pool."""
    return _get_pooled_conn(ms, autocommit=autocommit)


def mysql_connect(ms: MysqlSettings, *, autocommit: bool = False):
    """Backward compatibility alias for mysql_get_connection."""
    return mysql_get_connection(ms, autocommit=autocommit)


def mysql_sync_connect(ms: MysqlSettings, *, autocommit: bool = False) -> Any:
    """TDX 全量同步专用直连（长 read/write timeout，不占连接池）。"""
    from app.core.runtime_config import get_runtime_int

    read_timeout = max(60, get_runtime_int("TDX_MYSQL_READ_TIMEOUT", 600))
    write_timeout = max(60, get_runtime_int("TDX_MYSQL_WRITE_TIMEOUT", 600))
    return pymysql.connect(
        host=ms.host,
        port=ms.port,
        user=ms.user,
        password=ms.password,
        database=ms.database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=autocommit,
        connect_timeout=30,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
        **_mysql_ssl_args(),
    )


def dispose_mysql_engines(ms: MysqlSettings) -> None:
    """全量同步前释放本进程 SQLAlchemy 连接池。"""
    from .orm import dispose_engine_for_uri

    dispose_engine_for_uri(mysql_database_uri(ms))


def mysql_admin_connect(ms: MysqlSettings, *, autocommit: bool = False) -> Any:
    """绕过连接池的单连接（TRUNCATE 等管理操作）。"""
    return pymysql.connect(
        host=ms.host,
        port=ms.port,
        user=ms.user,
        password=ms.password,
        database=ms.database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=autocommit,
        connect_timeout=10,
        read_timeout=120,
        write_timeout=120,
        **_mysql_ssl_args(),
    )


def mysql_admin_execute(
    ms: MysqlSettings,
    sql: str,
    *,
    retries: int = 5,
    retry_sleep_sec: float = 3.0,
) -> None:
    """执行单条 DDL/DML（直连 + 1040 重试）。"""
    import time

    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        conn = None
        try:
            dispose_mysql_engines(ms)
            conn = mysql_admin_connect(ms, autocommit=False)
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            return
        except pymysql.err.OperationalError as exc:
            last_exc = exc
            if exc.args and int(exc.args[0]) == 1040 and attempt < retries - 1:
                logger.warning("MySQL 1040, retry admin SQL in %.0fs (%s)", retry_sleep_sec, attempt + 1)
                time.sleep(retry_sleep_sec)
                continue
            raise
        except Exception as exc:
            last_exc = exc
            raise
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_client.mysql_admin_execute: %s", e)
    if last_exc is not None:
        raise last_exc


def mysql_get_thread_local_connection(ms: MysqlSettings) -> Any:
    """
    Returns a pooled connection cached in thread-local storage.
    Legacy code relies on this to avoid manual .close() per call.
    MUST call mysql_close_thread_local_connection() at request end.
    """
    return _get_or_create_tl_conn(ms, "mysql_conn")


def mysql_get_read_connection(ms: MysqlSettings) -> Any:
    """Thread-local cached只读连接。"""
    return _get_or_create_tl_conn(ms, "mysql_read_conn")


def _get_or_create_tl_conn(ms: MysqlSettings, attr: str) -> Any:
    """Get or create a thread-local connection (legacy behavior).

    This is maintained for backward compatibility. New code should use
    mysql_get_connection() directly and manage connections explicitly.
    """
    # 不再使用线程本地连接，直接返回一个新的连接
    # 这样可以确保连接在使用后被正确关闭，避免连接泄漏
    return _get_pooled_conn(ms, autocommit=False)


def mysql_close_thread_local_connection() -> None:
    """
    Closes any thread-local pooled connections, returning them to the engine pool.
    This should be called in Flask teardown.
    """
    for attr in ["mysql_conn", "mysql_read_conn"]:
        conn = getattr(_tls, attr, None)
        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_client.py.mysql_close_thread_local_connection: %s", e)
            setattr(_tls, attr, None)


def ensure_mysql_schema(conn: Any = None) -> None:
    """Legacy DDL no-op."""
    logger.info("ensure_mysql_schema: no-op. Use Alembic.")


def row_to_dict(row: Any) -> dict[str, Any]:
    if row is None: return {}
    if isinstance(row, dict): return dict(row)
    try:
        return {k: row[k] for k in row.keys()}
    except (AttributeError, TypeError):
        return dict(row)
