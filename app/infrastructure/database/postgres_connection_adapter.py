from __future__ import annotations
"""Infrastructure adapter for PostgreSQL / TimescaleDB connections."""

from typing import Any

from app.domain.exceptions import ValidationError
from app.infrastructure.database.postgres_client import ensure_timescaledb_extension, postgres_connect
from app.infrastructure.database.postgres_settings import PostgresSettings


class PostgresConnectionAdapter:
    def __init__(self, postgres: PostgresSettings) -> None:
        self._postgres = postgres

    def connect(self, *, autocommit: bool = False) -> Any:
        return postgres_connect(self._postgres, autocommit=autocommit)

    def ensure_timescaledb(self, conn: Any | None = None) -> None:
        owned = conn is None
        conn = conn or self.connect(autocommit=False)
        try:
            ensure_timescaledb_extension(conn)
        finally:
            if owned:
                conn.close()


class NullPostgresConnectionPort:
    def connect(self, *, autocommit: bool = False) -> Any:
        raise ValidationError("timescaledb_not_enabled")

    def ensure_timescaledb(self, conn: Any | None = None) -> None:
        raise ValidationError("timescaledb_not_enabled")
