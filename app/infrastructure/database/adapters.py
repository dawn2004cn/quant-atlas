from __future__ import annotations

"""Database Adapter - Bridge Pattern for SQLite/MySQL."""


import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any

from app.core.logger import get_logger
from app.core.utils.sql_utils import validate_identifier

from ...config import INSTANCE_DIR, AppSettings, get_settings
from .mysql_client import mysql_get_connection

logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """Abstract database adapter - Implementor in Bridge Pattern."""

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Return parameter placeholder ('?' for SQLite, '%s' for MySQL)."""
        pass

    @abstractmethod
    def get_connection(self) -> Any:
        """Get write connection."""
        pass

    @abstractmethod
    def get_read_connection(self) -> Any:
        """Get read connection."""
        pass

    @abstractmethod
    def execute_many(self, sql: str, params: list[tuple]) -> None:
        """Execute many rows."""
        pass

    @abstractmethod
    def execute_select(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute select and return list of dict."""
        pass

    @abstractmethod
    def execute_scalar(self, sql: str, params: tuple = ()) -> Any:
        """Execute scalar query."""
        pass

    @contextmanager
    def transaction(self):
        """Context manager for transaction."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._close_if_needed(conn)

    @abstractmethod
    def _close_if_needed(self, conn: Any) -> None:
        """Close connection if needed."""
        pass


class SqliteAdapter(DatabaseAdapter):
    """SQLite adapter - Concrete Implementor."""

    _local = threading.local()

    @property
    def placeholder(self) -> str:
        return "?"

    def __init__(self, db_path: str):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()
        self._migrate_columns()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    price REAL,
                    change_pct REAL,
                    change_amount REAL DEFAULT 0,
                    prev_close REAL DEFAULT 0,
                    volume REAL,
                    amount REAL,
                    turnover REAL,
                    volume_ratio REAL DEFAULT 0,
                    amplitude REAL DEFAULT 0,
                    pe REAL DEFAULT 0,
                    pb REAL DEFAULT 0,
                    total_market_cap REAL DEFAULT 0,
                    industry TEXT DEFAULT '',
                    update_time TEXT
                )
            """)
            markets = ['sh', 'sz', 'bj', 'hk', 'us', 'btc']
            for market in markets:
                # Allowlisted suffix only — do not MySQL-backtick (breaks SQLite DDL).
                if not validate_identifier(market):
                    raise ValueError(f"unsafe market table suffix: {market!r}")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS stock_history_{market} (
                        stock_code TEXT,
                        date TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        amount REAL,
                        PRIMARY KEY(stock_code, date)
                    )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    stock_code TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    amount REAL,
                    PRIMARY KEY(stock_code, date)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_adjustment_factor (
                    stock_code TEXT NOT NULL,
                    date TEXT NOT NULL,
                    factor REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (stock_code, date)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_factor_stock ON stock_adjustment_factor(stock_code)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_factor_date ON stock_adjustment_factor(date)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_sentiment (
                    market TEXT PRIMARY KEY,
                    up_count INTEGER,
                    down_count INTEGER,
                    flat_count INTEGER,
                    total_count INTEGER,
                    update_time TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_sentiment_daily (
                    market TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    up_count INTEGER,
                    down_count INTEGER,
                    flat_count INTEGER,
                    total_count INTEGER,
                    update_time TEXT,
                    PRIMARY KEY (market, trade_date)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _migrate_columns(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(stocks)")
            have = {str(r[1]) for r in cur.fetchall()}
            specs = [
                ("change_amount", "REAL DEFAULT 0"),
                ("prev_close", "REAL DEFAULT 0"),
                ("volume_ratio", "REAL DEFAULT 0"),
                ("amplitude", "REAL DEFAULT 0"),
                ("pe", "REAL DEFAULT 0"),
                ("pb", "REAL DEFAULT 0"),
                ("total_market_cap", "REAL DEFAULT 0"),
                ("industry", "TEXT DEFAULT ''"),
            ]
            for col, decl in specs:
                if col not in have:
                    if not validate_identifier(col):
                        logger.warning("Skipping invalid column name in migration: %s", col)
                        continue
                    # Validated allowlisted column names; avoid MySQL backticks on SQLite.
                    cur.execute(f"ALTER TABLE stocks ADD COLUMN {col} {decl}")
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self._db_path, timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-10000")
            self._local.conn = conn
        return self._local.conn

    def get_connection(self) -> sqlite3.Connection:
        return self._get_conn()

    def get_read_connection(self) -> sqlite3.Connection:
        return self._get_conn()

    def execute_many(self, sql: str, params: list[tuple]) -> None:
        conn = self._get_conn()
        conn.executemany(sql, params)
        conn.commit()

    def execute_select(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def execute_scalar(self, sql: str, params: tuple = ()) -> Any:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None

    def _close_if_needed(self, conn: Any) -> None:
        pass


class MysqlAdapter(DatabaseAdapter):
    """MySQL adapter - Concrete Implementor."""

    @property
    def placeholder(self) -> str:
        return "%s"

    def __init__(self, mysql_config):
        self._mysql = mysql_config

    def get_connection(self):
        return mysql_get_connection(self._mysql, autocommit=True)

    def get_read_connection(self):
        return mysql_get_connection(self._mysql, autocommit=False)

    def execute_many(self, sql: str, params: list[tuple]) -> None:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.executemany(sql, params)
        conn.commit()
        cur.close()
        conn.close()

    def execute_select(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        conn = self.get_read_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        result = [dict(zip(columns, r)) for r in rows]
        cur.close()
        conn.close()
        return result

    def execute_scalar(self, sql: str, params: tuple = ()) -> Any:
        conn = self.get_read_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        result = row[0] if row else None
        cur.close()
        conn.close()
        return result

    def _close_if_needed(self, conn: Any) -> None:
        if conn:
            conn.close()


def create_database_adapter(settings: AppSettings | None = None) -> DatabaseAdapter:
    """Factory function to create database adapter based on settings."""
    if settings is None:
        settings = get_settings()

    (os.getenv("DATABASE_BACKEND") or settings.database_backend or "").strip().lower()

    if settings.use_mysql and settings.mysql is not None:
        return MysqlAdapter(settings.mysql)
    else:
        db_path = os.getenv("DATABASE_PATH") or str(INSTANCE_DIR / "stock_cache.db")
        return SqliteAdapter(db_path)
