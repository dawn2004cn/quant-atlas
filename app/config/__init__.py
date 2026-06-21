from __future__ import annotations

"""Configuration package — use get_settings() for application settings.

Settings are loaded from environment variables and optional .env file
via Pydantic Settings. Backward-compatible shims for get_runtime() /
get_runtime_bool() / get_runtime_int() are provided in settings.py.
"""

from app.config.settings import (
    AppSettings,
    CeleryConfig,
    DatabaseConfig,
    DatabaseSettings,
    FrontendConfig,
    MysqlSettings,
    PostgresSettings,
    QmtConfig,
    RedisConfig,
    ThsConfig,
    TdxConfig,
    TdxServersConfig,
    WechatConfig,
    AppEnvironment,
    DatabaseBackend,
    BASE_DIR,
    CONFIG_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_MODEL_REGISTRY_PATH,
    INSTANCE_DIR,
    get_runtime,
    get_runtime_bool,
    get_runtime_int,
    get_runtime_float,
    get_settings,
    reset_settings,
)

__all__ = [
    # Settings
    "AppSettings",
    "AppEnvironment",
    "DatabaseBackend",
    "DatabaseConfig",
    "DatabaseSettings",
    "MysqlSettings",
    "PostgresSettings",
    "CeleryConfig",
    "RedisConfig",
    "TdxConfig",
    "TdxServersConfig",
    "FrontendConfig",
    "WechatConfig",
    "QmtConfig",
    "ThsConfig",
    "get_settings",
    "reset_settings",
    # Legacy shim (deprecated)
    "get_runtime",
    "get_runtime_bool",
    "get_runtime_int",
    "get_runtime_float",
    # Constants
    "BASE_DIR",
    "CONFIG_DIR",
    "DEFAULT_DB_PATH",
    "DEFAULT_MODEL_REGISTRY_PATH",
    "INSTANCE_DIR",
]
