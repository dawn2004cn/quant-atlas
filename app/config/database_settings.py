"""Application settings loaded from environment via Pydantic Settings.

This module consolidates the legacy dataclass-based ``AppSettings``,
the INI/env hybrid ``runtime_config``, and the abandoned Pydantic
YAML approach into a single ``pydantic-settings`` hierarchy.

Loading order (highest → lowest priority):
    1. Process environment variables (always wins)
    2. ``.env`` file at repository root (``python-dotenv``, only fills missing)
    3. ``config/settings-{env}.yaml`` (optional, per-environment)
    4. ``config/settings.yaml`` (optional, base overrides)
    5. Default values (hardcoded in field definitions)

All previous env-var names are preserved as ``alias`` for backward compat:
- Old ``FLASK_DEBUG`` → new ``FLASK_DEBUG`` (same name)
- Old ``DATABASE_BACKEND`` → new ``DATABASE_BACKEND``
- Old ``TDX_ROOT_PATH`` → new ``TDX_ROOT_PATH``
- etc.

Migration strategy:
    - Old ``get_runtime()`` / ``get_runtime_bool()`` / ``get_runtime_int()``
      functions continue to work (they read os.environ / INI file).
    - New code should use ``get_settings()`` which returns a frozen
      ``AppSettings`` instance.
    - ``runtime_config.py`` will be deprecated and removed in a future phase.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Path constants ────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = _BASE_DIR
_CONFIG_DIR = _BASE_DIR / "config"
_INSTANCE_DIR = _BASE_DIR / "instance"
_DEFAULT_DB_PATH = _INSTANCE_DIR / "app_state_sqlite.db"


def _default_db_path() -> Path:
    """
    Default SQLite DB path.

    Tests monkeypatch ``app.config.settings.INSTANCE_DIR`` to an isolated temp
    directory. To respect that, we read the value lazily at runtime.
    """
    try:
        from app.config.settings import INSTANCE_DIR as _patched_instance_dir  # type: ignore

        return _patched_instance_dir / "app_state_sqlite.db"
    except Exception:
        return _DEFAULT_DB_PATH
_DEFAULT_MODEL_REGISTRY_PATH = _CONFIG_DIR / "model_registry.json"
DEFAULT_NETWORK_MASK = os.getenv("DEFAULT_NETWORK_MASK", os.getenv("DEFAULT_NETWORK_MASK", "127.0.0.0/8")).strip()


# ── Environment enum ──────────────────────────────────────────────────



class AppEnvironment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseBackend(str, Enum):
    """Database backend selection."""
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRES = "postgres"
    TIMESCALEDB = "timescaledb"


class DatabaseSettings(BaseModel, frozen=True):
    """A single database connection configuration."""

    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "quant_atlas"
    password: str = ""
    database: str = "quant_atlas"

    def describe(self) -> str:
        return f"{self._dialect()}://{self.user}@{self.host}:{self.port}/{self.database}"

    def _dialect(self) -> str:
        return "mysql" if "mysql" in os.getenv("DATABASE_BACKEND", "sqlite") else "postgresql"


class MysqlSettings(DatabaseSettings, frozen=True):
    """MySQL connection parameters."""

    port: int = 3306

    def _dialect(self) -> str:
        return "mysql"


class PostgresSettings(DatabaseSettings, frozen=True):
    """PostgreSQL / TimescaleDB connection parameters."""

    port: int = 5432

    def describe(self) -> str:
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"


class DatabaseConfig(BaseModel, frozen=True):
    """Database selection and concrete connection settings."""

    model_config = ConfigDict(populate_by_name=True)

    database_backend: str = Field(
        default="sqlite",
        validation_alias="DATABASE_BACKEND",
    )

    # MySQL
    mysql_host: str = Field(default="127.0.0.1", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_user: str = Field(default="quant_atlas", validation_alias="MYSQL_USER")
    mysql_password: str = Field(default="", validation_alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="quant_atlas", validation_alias="MYSQL_DATABASE")
    mysql_read_host: str = Field(default="", validation_alias="MYSQL_READ_HOST")

    # PostgreSQL / TimescaleDB
    postgres_host: str = Field(default="127.0.0.1", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(default="quant_atlas", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="", validation_alias="POSTGRES_PASSWORD")
    postgres_database: str = Field(default="quant_atlas", validation_alias="POSTGRES_DATABASE")
    timescaledb_host: str = Field(default="", validation_alias="TIMESCALEDB_HOST")
    timescaledb_port: int = Field(default=5432, validation_alias="TIMESCALEDB_PORT")
    timescaledb_user: str = Field(default="quant_atlas", validation_alias="TIMESCALEDB_USER")
    timescaledb_password: str = Field(default="", validation_alias="TIMESCALEDB_PASSWORD")
    timescaledb_database: str = Field(default="quant_atlas", validation_alias="TIMESCALEDB_DATABASE")
    use_timescaledb: bool = Field(default=False, validation_alias="USE_TIMESCALEDB")

    # SQLite
    sqlite_path: Path = Field(default_factory=_default_db_path)

    @model_validator(mode="before")
    @classmethod
    def _merge_flat_env(cls, data: Any) -> Any:
        from app.core.runtime_config import _load_dotenv_if_present

        _load_dotenv_if_present()
        merged: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
        env_map = {
            "database_backend": "DATABASE_BACKEND",
            "mysql_host": "MYSQL_HOST",
            "mysql_port": "MYSQL_PORT",
            "mysql_user": "MYSQL_USER",
            "mysql_password": "MYSQL_PASSWORD",
            "mysql_database": "MYSQL_DATABASE",
            "mysql_read_host": "MYSQL_READ_HOST",
            "postgres_host": "POSTGRES_HOST",
            "postgres_port": "POSTGRES_PORT",
            "postgres_user": "POSTGRES_USER",
            "postgres_password": "POSTGRES_PASSWORD",
            "postgres_database": "POSTGRES_DATABASE",
            "timescaledb_host": "TIMESCALEDB_HOST",
            "timescaledb_port": "TIMESCALEDB_PORT",
            "timescaledb_user": "TIMESCALEDB_USER",
            "timescaledb_password": "TIMESCALEDB_PASSWORD",
            "timescaledb_database": "TIMESCALEDB_DATABASE",
            "use_timescaledb": "USE_TIMESCALEDB",
        }
        for field, env_key in env_map.items():
            val = os.getenv(env_key)
            if val is None or str(val).strip() == "":
                continue
            merged[field] = val
        return merged

    @field_validator("use_timescaledb", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return value

    @property
    def backend(self) -> DatabaseBackend:
        raw = (self.database_backend or "sqlite").strip().lower()
        try:
            return DatabaseBackend(raw)
        except ValueError:
            return DatabaseBackend.SQLITE

    @property
    def use_mysql(self) -> bool:
        if self.backend == DatabaseBackend.MYSQL:
            return True
        use_mysql_env = os.getenv("USE_MYSQL", "false").lower() in ("true", "1", "yes")
        return use_mysql_env

    @property
    def use_postgres(self) -> bool:
        # use_timescaledb=1 时强制启用 postgres（即使 backend=mysql）
        if self.use_timescaledb:
            return True
        if self.backend == DatabaseBackend.MYSQL:
            return False
        if self.backend in (DatabaseBackend.POSTGRES, DatabaseBackend.TIMESCALEDB):
            return True
        ts_host = (self.timescaledb_host or self.postgres_host or "").strip()
        return bool(ts_host)

    @cached_property
    def mysql(self) -> MysqlSettings | None:
        if not self.use_mysql:
            return None
        return MysqlSettings(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database,
        )

    @cached_property
    def mysql_read(self) -> MysqlSettings:
        if self.mysql:
            if self.mysql_read_host:
                return MysqlSettings(
                    host=self.mysql_read_host,
                    port=self.mysql_port,
                    user=self.mysql_user,
                    password=self.mysql_password,
                    database=self.mysql_database,
                )
            return self.mysql
        # Fallback mirror even when not explicitly MySQL
        return MysqlSettings(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database,
        )

    @cached_property
    def postgres(self) -> PostgresSettings | None:
        if not self.use_postgres:
            return None
        host = self.timescaledb_host or self.postgres_host
        port = self.timescaledb_port if self.timescaledb_host else self.postgres_port
        user = self.timescaledb_user if self.timescaledb_host else self.postgres_user
        password = self.timescaledb_password if self.timescaledb_host else self.postgres_password
        database = self.timescaledb_database if self.timescaledb_host else self.postgres_database
        return PostgresSettings(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )

    @property
    def effective_backend(self) -> str:
        """Return the backend string used to build the URI."""
        if self.use_mysql:
            return "mysql"
        if self.use_postgres:
            return "timescaledb"
        return "sqlite"

    @cached_property
    def database_uri(self) -> str:
        """Build the SQLAlchemy database URI from resolved settings."""
        if self.use_mysql and self.mysql:
            from urllib.parse import quote_plus
            pwd = quote_plus(self.mysql.password)
            return f"mysql+pymysql://{quote_plus(self.mysql.user)}:{pwd}@{self.mysql.host}:{self.mysql.port}/{self.mysql.database}"

        if self.use_postgres and self.postgres:
            from urllib.parse import quote_plus
            pwd = quote_plus(self.postgres.password)
            return f"postgresql+psycopg://{quote_plus(self.postgres.user)}:{pwd}@{self.postgres.host}:{self.postgres.port}/{self.postgres.database}"

        # SQLite (default)
        uri = os.getenv("QUANT_DATABASE_URI", f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}")
        return uri


class RedisConfig(BaseModel, frozen=True):
    """Redis connection for cache / Celery / task messages."""

    host: str = Field(default="127.0.0.1", validation_alias="REDIS_HOST")
    port: int = Field(default=6379, validation_alias="REDIS_PORT")
    password: str = ""
    db: int = 0

    @cached_property
    def broker_url(self) -> str:
        return f"redis://{self.host}:{self.port}/0"


