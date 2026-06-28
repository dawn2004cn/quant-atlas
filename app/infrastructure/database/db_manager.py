from __future__ import annotations

"""Database connection manager with SQLAlchemy connection pooling."""

import re
import time
from typing import Any

from sqlalchemy import event

from app.core.logger import get_logger
from app.core.logging_config import SQL_LOGGER_NAME
from app.core.tracing.tracer import get_context_snapshot, get_trace_id, restore_context

from .mysql_settings import MysqlSettings
from .orm import create_db_engine, create_session_factory, mysql_database_uri, mysql_engine_kwargs

logger = get_logger(__name__)
sql_logger = get_logger(SQL_LOGGER_NAME)

# Regex to mask common sensitive patterns in SQL strings
_SENSITIVE_PATTERNS = [
    (re.compile(r"(password|passwd|pwd)\s*=\s*['\"]?[^'\"\s,)]+", re.I), "[REDACTED_CREDENTIAL]"),
    (re.compile(r"(token|api_key|secret)\s*=\s*['\"]?[^'\"\s,)]+", re.I), "[REDACTED_TOKEN]"),
]


def _mask_sql(sql: str) -> str:
    """Remove sensitive data from SQL statements for safe logging."""
    cleaned = sql.strip()
    # Truncate long queries
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "..."
    # Mask known sensitive patterns
    for pattern, replacement in _SENSITIVE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    # Remove SQL comments
    cleaned = re.sub(r"--.*$", "", cleaned, flags=re.MULTILINE).strip()
    return cleaned


def setup_db_monitoring(engine):
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()
        context._trace_snapshot = get_context_snapshot()
        # Store masked SQL for safe logging
        context._masked_sql = _mask_sql(str(statement)) if statement else ""

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, "_query_start_time"):
            total = time.perf_counter() - context._query_start_time

            if hasattr(context, "_trace_snapshot"):
                restore_context(context._trace_snapshot)

            trace_id = get_trace_id()
            # Use masked SQL from before_cursor_execute, fall back to sanitized statement
            sql_display = getattr(context, "_masked_sql", None)
            if not sql_display:
                sql_display = _mask_sql(str(statement)) if statement else "(empty)"
            sql_logger.info(
                "[SQL_TRACE] Time: %.2fms | TraceID: %s | Query: %s",
                total * 1000, trace_id, sql_display,
            )


class DatabaseManager:
    """Database connection manager."""

    def __init__(self):
        self._engines: dict[str, Any] = {}
        self._session_factories: dict[str, Any] = {}

    def get_engine(self, ms: MysqlSettings) -> Any:
        key = self._get_engine_key(ms)
        if key not in self._engines:
            uri = mysql_database_uri(ms)
            engine = create_db_engine(uri, **mysql_engine_kwargs())
            setup_db_monitoring(engine)
            self._engines[key] = engine
            logger.info("Created new engine for %s@%s:%s", ms.database, ms.host, ms.port)
        return self._engines[key]

    def get_session_factory(self, ms: MysqlSettings) -> Any:
        key = self._get_engine_key(ms)
        if key not in self._session_factories:
            engine = self.get_engine(ms)
            session_factory = create_session_factory(engine)
            self._session_factories[key] = session_factory
        return self._session_factories[key]

    def get_session(self, ms: MysqlSettings) -> Any:
        session_factory = self.get_session_factory(ms)
        return session_factory()

    def get_connection(self, ms: MysqlSettings, *, autocommit: bool = False) -> Any:
        engine = self.get_engine(ms)
        conn = engine.raw_connection()
        try:
            conn.autocommit(bool(autocommit))
        except Exception as e:
            logger.warning("db_manager.py.get_connection: %s", e)
        return conn

    def bootstrap_schema(self, ms: MysqlSettings) -> None:
        from .schema_bootstrap import bootstrap_schema as _bootstrap_schema
        engine = self.get_engine(ms)
        _bootstrap_schema(engine)
        logger.info("Bootstrapped schema for %s", ms.database)

    def _get_engine_key(self, ms: MysqlSettings) -> str:
        return f"{ms.host}:{ms.port}:{ms.database}:{ms.user}"


# Singleton instance
_db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get the singleton database manager instance."""
    return _db_manager


def get_engine(ms: MysqlSettings) -> Any:
    """Get a SQLAlchemy engine for the given MySQL settings."""
    return get_db_manager().get_engine(ms)


def get_session(ms: MysqlSettings) -> Any:
    """Get a scoped session for the given MySQL settings."""
    return get_db_manager().get_session(ms)


def get_connection(ms: MysqlSettings, *, autocommit: bool = False) -> Any:
    """Get a DBAPI connection from the connection pool."""
    return get_db_manager().get_connection(ms, autocommit=autocommit)


def bootstrap_schema(ms: MysqlSettings) -> None:
    """Bootstrap database schema."""
    get_db_manager().bootstrap_schema(ms)
