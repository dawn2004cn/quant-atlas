from __future__ import annotations

"""SQLAlchemy engine/session bootstrap helpers.

This module provides the canonical DB runtime scaffolding for MySQL-backed
deployments:
- Engine with real connection pooling
- Scoped session factory for repository assembly
- Optional schema bootstrap fallback (non-destructive create_all)
"""


import threading
from typing import Any
from urllib.parse import quote_plus

import pymysql
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from app.core.logger import get_logger

from ...core.runtime_config import get_runtime_int
from .mysql_settings import MysqlSettings

logger = get_logger(__name__)
_ENGINE_CACHE: dict[str, Any] = {}
_ENGINE_LOCK = threading.Lock()


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def mysql_database_uri(ms: MysqlSettings) -> str:
    """Build SQLAlchemy MySQL URI from typed mysql settings."""
    return (
        f"mysql+pymysql://{quote_plus(ms.user or '')}:{quote_plus(ms.password or '')}"
        f"@{ms.host}:{int(ms.port)}/{ms.database}"
    )


def mysql_engine_kwargs() -> dict[str, Any]:
    """Centralized MySQL engine + pool configuration."""
    # Defaults are intentionally conservative to avoid exhausting MySQL `max_connections`
    # in multi-process deployments (gunicorn workers / celery concurrency).
    pool_size = max(1, get_runtime_int("DB_POOL_SIZE", 5))
    max_overflow = max(0, get_runtime_int("DB_MAX_OVERFLOW", 10))
    pool_recycle = max(60, get_runtime_int("DB_POOL_RECYCLE", 300))
    pool_timeout = max(5, get_runtime_int("DB_POOL_TIMEOUT", 30))
    connect_timeout = max(1, get_runtime_int("DB_CONNECT_TIMEOUT", 10))
    read_timeout = max(1, get_runtime_int("DB_READ_TIMEOUT", 60))
    write_timeout = max(1, get_runtime_int("DB_WRITE_TIMEOUT", 60))
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": pool_recycle,
        "pool_timeout": pool_timeout,
        "pool_pre_ping": True,
        "pool_use_lifo": True,
        "pool_reset_on_return": None,
        "connect_args": {
            "connect_timeout": connect_timeout,
            "read_timeout": read_timeout,
            "write_timeout": write_timeout,
            "charset": "utf8mb4",
        },
    }


def create_db_engine(database_uri: str, **kwargs: Any):
    """Create a SQLAlchemy engine.

    For MySQL/PostgreSQL, this enables real connection pooling.
    For SQLite, this keeps a minimal config suitable for local fallback.
    """
    uri = (database_uri or "").strip()
    if not uri:
        raise ValueError("database_uri is required to initialize SQLAlchemy engine")

    cached = _ENGINE_CACHE.get(uri)
    if cached is not None:
        return cached

    with _ENGINE_LOCK:
        cached = _ENGINE_CACHE.get(uri)
        if cached is not None:
            return cached

        if uri.startswith("sqlite"):
            pool_pre_ping = kwargs.pop("pool_pre_ping", True)
            eng = create_engine(
                uri,
                future=True,
                pool_pre_ping=pool_pre_ping,
                connect_args={"check_same_thread": False},
                **kwargs,
            )
            _ENGINE_CACHE[uri] = eng
            return eng

        pool_size = kwargs.pop("pool_size", 2)
        max_overflow = kwargs.pop("max_overflow", 3)
        pool_recycle = kwargs.pop("pool_recycle", 30)
        pool_timeout = kwargs.pop("pool_timeout", 5)
        pool_pre_ping = kwargs.pop("pool_pre_ping", True)
        pool_use_lifo = kwargs.pop("pool_use_lifo", True)

        eng = create_engine(
            uri,
            future=True,
            pool_pre_ping=pool_pre_ping,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_timeout=pool_timeout,
            pool_use_lifo=pool_use_lifo,
            echo=False,
            **kwargs,
        )

        @event.listens_for(eng, "handle_error")
        def _handle_disconnect(context):
            exc = context.original_exception
            if exc is None:
                return
            if isinstance(exc, pymysql.err.InterfaceError) and exc.args[0] == 0:
                raise exc.DisconnectionError("Connection closed by server")
            try:
                if context.connection and context.connection.is_active:
                    context.connection.begin_nested()
            except Exception as e:
                logger.warning("orm.py.create_db_engine: %s", e)

        @event.listens_for(eng, "checkout")
        def _checkout_check(dbapi_connection, connection_record, connection_proxy):
            try:
                dbapi_connection.ping(reconnect=True)
            except Exception as exc:
                raise exc.DisconnectionError("Connection checkout failed") from exc

        @event.listens_for(eng, "connect")
        def _configure_connection(dbapi_connection, connection_record):
            try:
                dbapi_connection.ping(reconnect=True)
            except Exception as e:
                logger.warning("orm.py.create_db_engine: %s", e)

        _ENGINE_CACHE[uri] = eng
        return eng


def dispose_engine_for_uri(database_uri: str) -> None:
    """释放缓存引擎及池中连接（全量任务启动前调用，减轻 1040）。"""
    uri = (database_uri or "").strip()
    if not uri:
        return
    with _ENGINE_LOCK:
        eng = _ENGINE_CACHE.pop(uri, None)
    if eng is not None:
        try:
            eng.dispose()
            logger.info("Disposed SQLAlchemy engine for %s", uri.split("@")[-1])
        except Exception as exc:
            logger.warning("dispose_engine_for_uri: %s", exc)


def create_session_factory(engine):
    """Create a scoped session factory."""
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return scoped_session(session_factory)


def bootstrap_schema(engine) -> None:
    """Fallback schema bootstrap for repository assembly.

    Preferred path: ``alembic upgrade head`` (see ``schema_bootstrap``).
    This only creates missing tables when Alembic is disabled or fails.
    """
    from .schema_bootstrap import bootstrap_schema as _bootstrap_schema

    _bootstrap_schema(engine)
