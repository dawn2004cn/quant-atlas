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
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config.database_settings import AppEnvironment, DatabaseBackend, DatabaseConfig, MysqlSettings, PostgresSettings
from app.config.infra_settings import CeleryConfig, TdxConfig, FrontendConfig, WechatConfig, QmtConfig, ThsConfig

# ── Path constants ────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = _BASE_DIR
_CONFIG_DIR = _BASE_DIR / "config"
_INSTANCE_DIR = _BASE_DIR / "instance"
_DEFAULT_DB_PATH = _INSTANCE_DIR / "app_state_sqlite.db"
_DEFAULT_MODEL_REGISTRY_PATH = _CONFIG_DIR / "model_registry.json"
DEFAULT_NETWORK_MASK = os.getenv("DEFAULT_NETWORK_MASK", os.getenv("DEFAULT_NETWORK_MASK", "127.0.0.0/8")).strip()

# Flat .env keys → nested DatabaseConfig / TdxConfig fields (pydantic-settings
# only auto-binds top-level AppSettings fields from .env).
_DATABASE_NESTED_ENV: dict[str, str] = {
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

_TDX_NESTED_ENV: dict[str, str] = {
    "root_path": "TDX_ROOT_PATH",
    "finance_ingest_enabled": "TDX_FINANCE_INGEST_ENABLED",
    "rate_limit_rps": "TDX_FINANCE_RATE_LIMIT_RPS",
    "max_symbols_per_run": "TDX_FINANCE_MAX_SYMBOLS_PER_RUN",
    "watchlist_ingest_enabled": "TDX_WATCHLIST_INGEST_ENABLED",
    "watchlist_paths": "TDX_WATCHLIST_PATHS",
}


def _nested_env_section(
    payload: dict[str, Any],
    section: str,
    mapping: dict[str, str],
) -> None:
    block = dict(payload.get(section) or {})
    for field, env_key in mapping.items():
        val = os.getenv(env_key)
        if val is None or str(val).strip() == "":
            continue
        block[field] = val
    if block:
        payload[section] = block


# ── Environment enum ──────────────────────────────────────────────────



class AppSettings(BaseSettings, frozen=True):
    """Top-level application settings.

    All field names map 1:1 to the environment variable names the existing
    codebase expects, so zero code changes are needed in consumers —
    ``settings.tdx_root_path`` works the same as the old ``get_runtime("TDX_ROOT_PATH")``.
    """

    model_config = SettingsConfigDict(
        # Prefix for all env vars (e.g. FLASK_DEBUG → app.flask_debug env var)
        # We use NO prefix so env var names match field names directly.
        env_prefix="",
        # Allow alias resolution
        populate_by_name=True,
        # Extra fields forbidden to catch typos
        extra="ignore",
        # Use .env file if present
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    @model_validator(mode="before")
    @classmethod
    def _hydrate_nested_from_dotenv(cls, data: Any) -> Any:
        """Bind MYSQL_* / TDX_* flat keys into nested config models."""
        from app.core.runtime_config import _load_dotenv_if_present

        _load_dotenv_if_present()
        payload: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
        _nested_env_section(payload, "database", _DATABASE_NESTED_ENV)
        _nested_env_section(payload, "tdx", _TDX_NESTED_ENV)
        if isinstance(payload.get("database"), dict):
            db = payload["database"]
            top_backend = payload.get("database_backend") or os.getenv("DATABASE_BACKEND")
            if top_backend and not db.get("database_backend"):
                db["database_backend"] = top_backend
        return payload

    # ── Core ──────────────────────────────────────────────────────────

    # Flask
    secret_key: str = Field(default="", validation_alias="FLASK_SECRET_KEY")
    debug: bool = Field(default=False, validation_alias="FLASK_DEBUG")
    environment: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        validation_alias="FLASK_ENV",
    )

    # ── Feature toggles ──────────────────────────────────────────────

    enable_background_scanner: bool = Field(
        default=True, validation_alias="ENABLE_BACKGROUND_SCANNER",
    )
    scanner_force_threads: bool = Field(
        default=False, validation_alias="SCANNER_FORCE_THREADS",
    )
    enable_api_legacy_response_fields: bool = Field(
        default=False, validation_alias="ENABLE_API_LEGACY_RESPONSE_FIELDS",
    )
    enable_qlib: bool = Field(default=False, validation_alias="ENABLE_QLIB")
    enable_rd_agent: bool = Field(default=False, validation_alias="ENABLE_RD_AGENT")
    enable_basic_data_scheduler: bool = Field(
        default=True, validation_alias="ENABLE_BASIC_DATA_SCHEDULER",
    )

    # ── Database ─────────────────────────────────────────────────────

    database_backend: DatabaseBackend = Field(
        default=DatabaseBackend.SQLITE,
        validation_alias="DATABASE_BACKEND",
    )

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Aliases for backward compat: code that accesses settings.database_uri,
    # settings.use_mysql, settings.mysql, settings.postgres, etc. will still work via cached_property wrappers.
    @property
    def database_uri(self) -> str:
        return self.database.database_uri

    @property
    def use_mysql(self) -> bool:
        if self.database_backend == DatabaseBackend.MYSQL:
            return True
        return self.database.use_mysql

    @property
    def mysql(self) -> MysqlSettings | None:
        """Backward compat: was settings.mysql, now settings.database.mysql."""
        return self.database.mysql

    @property
    def postgres(self) -> PostgresSettings | None:
        """Backward compat: was settings.postgres, now settings.database.postgres."""
        return self.database.postgres

    @property
    def sqlite_path(self) -> Path:
        """Backward compat: was settings.sqlite_path, now settings.database.sqlite_path."""
        return self.database.sqlite_path

    @property
    def use_timescaledb(self) -> bool:
        return self.database.use_postgres

    @property
    def timescaledb_uri(self) -> str | None:
        pg = self.database.postgres
        if pg is None:
            return None
        from urllib.parse import quote_plus
        return (
            f"postgresql+psycopg://{quote_plus(pg.user)}:{quote_plus(pg.password)}"
            f"@{pg.host}:{pg.port}/{pg.database}"
        )

    # ── Celery ───────────────────────────────────────────────────────

    celery: CeleryConfig = Field(default_factory=CeleryConfig)

    redis_url: str = Field(default="", validation_alias="REDIS_URL")

    @property
    def resolved_redis_url(self) -> str:
        explicit = (self.redis_url or "").strip()
        if explicit:
            return explicit
        return self.celery.resolved_task_message_redis_url or self.celery.broker_url

    @property
    def enable_celery(self) -> bool:
        return self.celery.enabled

    @property
    def celery_broker_url(self) -> str:
        return self.celery.broker_url

    @property
    def celery_result_backend(self) -> str:
        return self.celery.resolved_result_backend

    @property
    def task_message_redis_url(self) -> str:
        return self.celery.resolved_task_message_redis_url

    # ── Storage paths ────────────────────────────────────────────────

    template_folder: str = str(_BASE_DIR / "app" / "presentation" / "web" / "templates")
    static_folder: str = str(_BASE_DIR / "static")
    user_store_path: Path = _CONFIG_DIR / "users.json"
    watchlist_store_path: Path = _CONFIG_DIR / "watchlist.json"
    stock_groups_store_path: Path = _CONFIG_DIR / "stock_groups.json"

    # ── TDX ──────────────────────────────────────────────────────────

    tdx: TdxConfig = Field(default_factory=TdxConfig)

    @property
    def tdx_root_path(self) -> str | None:
        return self.tdx.root_path or None

    @property
    def tdx_finance_ingest_enabled(self) -> bool:
        return self.tdx.finance_ingest_enabled

    @property
    def tdx_finance_rate_limit_rps(self) -> int:
        return self.tdx.rate_limit_rps

    @property
    def tdx_finance_max_symbols_per_run(self) -> int:
        return self.tdx.max_symbols_per_run

    @property
    def tdx_watchlist_ingest_enabled(self) -> bool:
        return self.tdx.watchlist_ingest_enabled

    @property
    def tdx_watchlist_paths(self) -> str:
        return self.tdx.watchlist_paths

    # ── Third-party integrations ─────────────────────────────────────

    fmp_api_key: str = Field(default="", validation_alias="FMP_API_KEY")

    fingpt_write_research_sentiment: bool = Field(
        default=True, validation_alias="FINGPT_WRITE_RESEARCH_SENTIMENT",
    )
    fingpt_write_research_prediction: bool = Field(
        default=True, validation_alias="FINGPT_WRITE_RESEARCH_PREDICTION",
    )
    fingpt_write_ai_analyze: bool = Field(
        default=True, validation_alias="FINGPT_WRITE_AI_ANALYZE",
    )

    # ── Optional subsystems ──────────────────────────────────────────

    wechat: WechatConfig = Field(default_factory=WechatConfig)

    @property
    def wechat_open_app_id(self) -> str | None:
        return self.wechat.app_id or None

    @property
    def wechat_open_app_secret(self) -> str | None:
        return self.wechat.app_secret or None

    @property
    def wechat_redirect_uri(self) -> str | None:
        return self.wechat.redirect_uri or None

    qmt: QmtConfig = Field(default_factory=QmtConfig)

    @property
    def qmt_account_id(self) -> str | None:
        return self.qmt.account_id or None

    @property
    def qmt_path(self) -> str | None:
        return self.qmt.qmt_path or None

    ths: ThsConfig = Field(default_factory=ThsConfig)

    @property
    def ths_username(self) -> str | None:
        return self.ths.username or None

    @property
    def ths_password(self) -> str | None:
        return self.ths.password or None

    # ── Frontend ─────────────────────────────────────────────────────

    frontend: FrontendConfig = Field(default_factory=FrontendConfig)

    @property
    def ui_color_scheme(self) -> str:
        return self.frontend.color_scheme

    # ── Security / HMAC secrets ───────────────────────────────────────

    cross_team_secret: str = Field(
        default="", validation_alias="CROSS_TEAM_SECRET",
    )

    @property
    def resolved_cross_team_secret(self) -> str:
        """Return configured cross-team secret or generate one at runtime."""
        if self.cross_team_secret:
            return self.cross_team_secret
        # Generate deterministic key from Flask secret (so restarts keep same key)
        return f"cross-team:{self.secret_key}"

    # ── Backward-compat aliases for code that still uses old names ───

    @property
    def mesh_enabled(self) -> bool:
        """Backward compat: was read from registry_config."""
        return False  # default; controlled via ENABLE_MESH env var in wiring

    @property
    def perception_enabled(self) -> bool:
        return False  # controlled via wiring config

    @property
    def enable_socketio(self) -> bool:
        return os.getenv("ENABLE_SOCKETIO", "false").lower() in ("true", "1", "yes")

    @property
    def enable_vision(self) -> bool:
        return os.getenv("ENABLE_VISION", "true").lower() in ("true", "1", "yes")

    @property
    def enable_collaboration(self) -> bool:
        return os.getenv("ENABLE_COLLABORATION", "true").lower() in ("true", "1", "yes")


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Return cached AppSettings; loads from env once per process."""
    global _settings
    if _settings is not None:
        return _settings
    from app.core.runtime_config import _load_dotenv_if_present

    _load_dotenv_if_present()
    _settings = AppSettings()  # type: ignore[call-arg]
    return _settings


def reset_settings() -> None:
    """Clear cache (tests only)."""
    global _settings
    _settings = None


# ── Public constants (re-exported by __init__.py) ────────────────────

BASE_DIR = _BASE_DIR
CONFIG_DIR = _CONFIG_DIR
INSTANCE_DIR = _INSTANCE_DIR
DEFAULT_DB_PATH = _DEFAULT_DB_PATH
DEFAULT_MODEL_REGISTRY_PATH = _DEFAULT_MODEL_REGISTRY_PATH


# ── Legacy runtime_config shim ─────────────────────────────────────────


# The following functions preserve the API of app.core.runtime_config
# so that existing callers (get_runtime, get_runtime_bool, etc.) don't
# break. They read from the Pydantic settings instead of the INI file.
# This shim will be removed once all callers migrate.

import functools



# Build a fast lookup: field path → setting attribute
_FIELD_CACHE: dict[str, Any] = {}


def _build_field_cache() -> None:
    """Populate _FIELD_CACHE with flattened setting paths."""
    global _FIELD_CACHE
    s = get_settings()
    # Core fields
    _FIELD_CACHE["secret_key"] = s.secret_key
    _FIELD_CACHE["debug"] = s.debug
    _FIELD_CACHE["enable_background_scanner"] = s.enable_background_scanner
    _FIELD_CACHE["scanner_force_threads"] = s.scanner_force_threads
    _FIELD_CACHE["enable_api_legacy_response_fields"] = s.enable_api_legacy_response_fields
    _FIELD_CACHE["enable_qlib"] = s.enable_qlib
    _FIELD_CACHE["enable_rd_agent"] = s.enable_rd_agent
    _FIELD_CACHE["enable_basic_data_scheduler"] = s.enable_basic_data_scheduler
    _FIELD_CACHE["database_uri"] = s.database_uri
    _FIELD_CACHE["database_backend"] = s.database.effective_backend
    _FIELD_CACHE["tdx_root_path"] = s.tdx_root_path
    _FIELD_CACHE["tdx_finance_ingest_enabled"] = s.tdx_finance_ingest_enabled
    _FIELD_CACHE["tdx_finance_rate_limit_rps"] = s.tdx_finance_rate_limit_rps
    _FIELD_CACHE["tdx_finance_max_symbols_per_run"] = s.tdx_finance_max_symbols_per_run
    _FIELD_CACHE["tdx_watchlist_ingest_enabled"] = s.tdx_watchlist_ingest_enabled
    _FIELD_CACHE["tdx_watchlist_paths"] = s.tdx_watchlist_paths
    _FIELD_CACHE["fingpt_write_research_sentiment"] = s.fingpt_write_research_sentiment
    _FIELD_CACHE["fingpt_write_research_prediction"] = s.fingpt_write_research_prediction
    _FIELD_CACHE["fingpt_write_ai_analyze"] = s.fingpt_write_ai_analyze
    _FIELD_CACHE["fmp_api_key"] = s.fmp_api_key
    _FIELD_CACHE["ui_color_scheme"] = s.ui_color_scheme
    _FIELD_CACHE["wechat_open_app_id"] = s.wechat_open_app_id
    _FIELD_CACHE["wechat_open_app_secret"] = s.wechat_open_app_secret
    _FIELD_CACHE["wechat_redirect_uri"] = s.wechat_redirect_uri
    _FIELD_CACHE["qmt_account_id"] = s.qmt_account_id
    _FIELD_CACHE["qmt_path"] = s.qmt_path
    _FIELD_CACHE["ths_username"] = s.ths_username
    _FIELD_CACHE["ths_password"] = s.ths_password
    # Bool/env-only aliases
    _FIELD_CACHE["USE_MYSQL"] = s.database.use_mysql
    _FIELD_CACHE["USE_TIMESCALEDB"] = s.database.use_postgres
    _FIELD_CACHE["ENABLE_VISION"] = True  # default
    _FIELD_CACHE["ENABLE_COLLABORATION"] = True
    _FIELD_CACHE["ENABLE_SOCKETIO"] = s.enable_socketio
    _FIELD_CACHE["ENABLE_BACKGROUND_SCANNER"] = s.enable_background_scanner
    _FIELD_CACHE["SCANNER_FORCE_THREADS"] = s.scanner_force_threads
    _FIELD_CACHE["ENABLE_API_LEGACY_RESPONSE_FIELDS"] = s.enable_api_legacy_response_fields
    _FIELD_CACHE["ENABLE_QLIB"] = s.enable_qlib
    _FIELD_CACHE["ENABLE_RD_AGENT"] = s.enable_rd_agent
    _FIELD_CACHE["ENABLE_BASIC_DATA_SCHEDULER"] = s.enable_basic_data_scheduler
    _FIELD_CACHE["ENABLE_CELERY"] = s.celery.enabled
    _FIELD_CACHE["CELERY_BROKER_URL"] = s.celery.broker_url
    _FIELD_CACHE["CELERY_RESULT_BACKEND"] = s.celery.resolved_result_backend
    _FIELD_CACHE["TASK_MESSAGE_REDIS_URL"] = s.celery.resolved_task_message_redis_url
    _FIELD_CACHE["REDIS_URL"] = s.resolved_redis_url
    _FIELD_CACHE["UI_COLOR_SCHEME"] = s.ui_color_scheme
    _FIELD_CACHE["ENABLE_BACKGROUND_SCANNER"] = s.enable_background_scanner
    _FIELD_CACHE["ENABLE_TDX_FINANCE_INGEST"] = s.tdx.finance_ingest_enabled
    _FIELD_CACHE["FINGPT_WRITE_RESEARCH_SENTIMENT"] = s.fingpt_write_research_sentiment
    _FIELD_CACHE["FINGPT_WRITE_RESEARCH_PREDICTION"] = s.fingpt_write_research_prediction
    _FIELD_CACHE["FINGPT_WRITE_AI_ANALYZE"] = s.fingpt_write_ai_analyze
    _FIELD_CACHE["FMP_API_KEY"] = s.fmp_api_key
    _FIELD_CACHE["THS_USERNAME"] = s.ths_username
    _FIELD_CACHE["THS_PASSWORD"] = s.ths_password
    _FIELD_CACHE["QMT_ACCOUNT_ID"] = s.qmt_account_id
    _FIELD_CACHE["QMT_PATH"] = s.qmt_path
    _FIELD_CACHE["TDX_ROOT_PATH"] = s.tdx_root_path or ""
    _FIELD_CACHE["TDX_WATCHLIST_PATHS"] = s.tdx_watchlist_paths
    _FIELD_CACHE["TDX_FINANCE_INGEST_ENABLED"] = s.tdx.finance_ingest_enabled
    _FIELD_CACHE["TDX_FINANCE_RATE_LIMIT_RPS"] = s.tdx.rate_limit_rps
    _FIELD_CACHE["TDX_FINANCE_MAX_SYMBOLS_PER_RUN"] = s.tdx.max_symbols_per_run


@functools.lru_cache(maxsize=1)
def _ensure_field_cache() -> None:
    _build_field_cache()


# Keys that only come from env (not from settings fallback)
_ENV_ONLY_KEYS: frozenset[str] = frozenset(
    {
        "FLASK_SECRET_KEY",
        "QUANT_DATABASE_URI",
        "WECHAT_OPEN_APP_SECRET",
        "OPENAI_API_KEY",
        "LANGGRAPH_POSTGRES_URI",
        "DATABASE_URL",
        "RDAGENT_WEBHOOK_URL",
    }
)


def get_runtime(key: str, default: str = "") -> str:
    """Backward-compat: read a config value.

    Priority:
    1. Process environment variable (os.environ)
    2. Pydantic settings field value
    3. *default*

    .. deprecated::
        Use ``get_settings().<field>`` or a direct env var read instead.
    """
    if key in _ENV_ONLY_KEYS:
        return (os.getenv(key) or default).strip()
    ev = os.getenv(key)
    if ev is not None and str(ev).strip() != "":
        return str(ev).strip()
    _ensure_field_cache()
    return _FIELD_CACHE.get(key, default)


def get_runtime_bool(key: str, default: bool = False) -> bool:
    """Backward-compat: read a boolean config value."""
    raw = get_runtime(key, "1" if default else "0")
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def get_runtime_int(key: str, default: int) -> int:
    """Backward-compat: read an integer config value."""
    raw = get_runtime(key, str(default))
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def get_runtime_float(key: str, default: float) -> float:
    """Backward-compat: read a float config value."""
    raw = get_runtime(key, str(default))
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default
