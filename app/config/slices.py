from __future__ import annotations

"""Frozen configuration slices injected into services (subset of AppSettings).

.. deprecated::
    These slices are now handled inline by ``AppSettings`` in ``app.config.settings``.
    This module is retained for backward-compat only.
"""

from dataclasses import dataclass
from pathlib import Path

from app.infrastructure.database.mysql_settings import MysqlSettings
from app.infrastructure.database.postgres_settings import PostgresSettings


@dataclass(frozen=True)
class DataBackendSettings:
    database_backend: str
    database_uri: str
    sqlite_path: Path
    mysql: MysqlSettings | None
    mysql_read: MysqlSettings | None
    postgres: PostgresSettings | None

    @property
    def use_mysql(self) -> bool:
        return (self.database_backend or "").lower() == "mysql" and self.mysql is not None

    @property
    def use_timescaledb(self) -> bool:
        if self.postgres is None:
            return False
        backend = (self.database_backend or "").lower()
        return backend in ("timescaledb", "postgresql", "postgres")


@dataclass(frozen=True)
class QmtExecutionSettings:
    account_id: str | None
    qmt_path: str | None

    @property
    def enabled(self) -> bool:
        return bool((self.account_id or "").strip())


@dataclass(frozen=True)
class ThsProviderSettings:
    username: str | None
    password: str | None

    @property
    def has_credentials(self) -> bool:
        return bool((self.username or "").strip() and (self.password or "").strip())
