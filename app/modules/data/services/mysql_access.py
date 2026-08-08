from __future__ import annotations
"""Bound MySQL connection port for application services (configured at bootstrap)."""

from typing import Any

from app.domain.ports.mysql_connection_port import MySQLConnectionPort

_port: MySQLConnectionPort | None = None


def bind_mysql_connection_port(port: MySQLConnectionPort) -> None:
    global _port
    _port = port


def get_mysql_connection_port() -> MySQLConnectionPort:
    if _port is None:
        raise RuntimeError(
            "MySQLConnectionPort not configured; bootstrap must call bind_mysql_connection_port()"
        )
    return _port


def mysql_connect(*, autocommit: bool = False) -> Any:
    return get_mysql_connection_port().connect(autocommit=autocommit)


def ensure_mysql_schema(conn: Any = None) -> None:
    get_mysql_connection_port().ensure_schema(conn)


def mysql_commit(conn: Any) -> None:
    get_mysql_connection_port().commit(conn)


def mysql_rollback(conn: Any) -> None:
    get_mysql_connection_port().rollback(conn)
