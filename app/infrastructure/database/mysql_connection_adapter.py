from __future__ import annotations

"""Infrastructure adapter for ``MySQLConnectionPort``."""

from typing import Any

from app.domain.exceptions import ValidationError
from app.infrastructure.database.mysql_client import ensure_mysql_schema, mysql_connect
from app.infrastructure.database.mysql_settings import MysqlSettings


class MySQLConnectionAdapter:
    def __init__(self, mysql: MysqlSettings) -> None:
        self._mysql = mysql

    def connect(self, *, autocommit: bool = False) -> Any:
        return mysql_connect(self._mysql, autocommit=autocommit)

    def connect_sync(self, *, autocommit: bool = False) -> Any:
        from app.infrastructure.database.mysql_client import mysql_sync_connect

        return mysql_sync_connect(self._mysql, autocommit=autocommit)

    def ensure_schema(self, conn: Any = None) -> None:
        ensure_mysql_schema(conn)

    def commit(self, conn: Any) -> None:
        conn.commit()

    def rollback(self, conn: Any) -> None:
        conn.rollback()

    def close(self, conn: Any) -> None:
        conn.close()


class NullMySQLConnectionPort:
    """Used when MySQL is disabled; operations fail with a clear validation error."""

    def connect(self, *, autocommit: bool = False) -> Any:
        raise ValidationError("mysql_not_enabled")

    def ensure_schema(self, conn: Any = None) -> None:
        raise ValidationError("mysql_not_enabled")

    def commit(self, conn: Any) -> None:
        raise ValidationError("mysql_not_enabled")

    def rollback(self, conn: Any) -> None:
        raise ValidationError("mysql_not_enabled")

    def close(self, conn: Any) -> None:
        raise ValidationError("mysql_not_enabled")
