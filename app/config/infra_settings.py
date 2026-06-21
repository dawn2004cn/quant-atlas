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
_DEFAULT_MODEL_REGISTRY_PATH = _CONFIG_DIR / "model_registry.json"


# ── Environment enum ──────────────────────────────────────────────────



class CeleryConfig(BaseModel, frozen=True):
    """Celery task queue configuration.

    ``result_backend`` and ``task_message_redis_url`` default to ``broker_url``
    if left empty.
    """

    enabled: bool = Field(default=False, validation_alias="ENABLE_CELERY")
    broker_url: str = Field(default="", validation_alias="CELERY_BROKER_URL")
    result_backend: str = Field(default="", validation_alias="CELERY_RESULT_BACKEND")
    task_message_redis_url: str = Field(default="", validation_alias="TASK_MESSAGE_REDIS_URL")

    @property
    def resolved_result_backend(self) -> str:
        return self.result_backend or self.broker_url

    @property
    def resolved_task_message_redis_url(self) -> str:
        return self.task_message_redis_url or self.broker_url


class TdxConfig(BaseModel, frozen=True):
    """TongDaxin (通达信) local data configuration."""

    model_config = ConfigDict(populate_by_name=True)

    root_path: str = Field(default="", validation_alias="TDX_ROOT_PATH")
    finance_ingest_enabled: bool = Field(
        default=False, validation_alias="TDX_FINANCE_INGEST_ENABLED",
    )
    rate_limit_rps: int = Field(default=2, validation_alias="TDX_FINANCE_RATE_LIMIT_RPS")
    max_symbols_per_run: int = Field(
        default=300, validation_alias="TDX_FINANCE_MAX_SYMBOLS_PER_RUN",
    )
    watchlist_ingest_enabled: bool = Field(
        default=False, validation_alias="TDX_WATCHLIST_INGEST_ENABLED",
    )
    watchlist_paths: str = Field(default="", validation_alias="TDX_WATCHLIST_PATHS")

    @model_validator(mode="before")
    @classmethod
    def _merge_flat_env(cls, data: Any) -> Any:
        from app.core.runtime_config import _load_dotenv_if_present

        _load_dotenv_if_present()
        merged: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
        for field, env_key in (
            ("root_path", "TDX_ROOT_PATH"),
            ("finance_ingest_enabled", "TDX_FINANCE_INGEST_ENABLED"),
            ("rate_limit_rps", "TDX_FINANCE_RATE_LIMIT_RPS"),
            ("max_symbols_per_run", "TDX_FINANCE_MAX_SYMBOLS_PER_RUN"),
            ("watchlist_ingest_enabled", "TDX_WATCHLIST_INGEST_ENABLED"),
            ("watchlist_paths", "TDX_WATCHLIST_PATHS"),
        ):
            val = os.getenv(env_key)
            if val is None or str(val).strip() == "":
                continue
            merged[field] = val
        return merged

    @field_validator("root_path", mode="before")
    @classmethod
    def _strip_empty(cls, v: Any) -> str:
        return (v or "").strip() or ""


class TdxServersConfig(BaseModel, frozen=True):
    """TDX server pool configuration."""

    servers_json: str = ""  # JSON override; empty → use built-in defaults
    ex_servers_json: str = ""


class FrontendConfig(BaseModel, frozen=True):
    """Frontend / UI configuration."""

    color_scheme: str = "cn"  # "cn" or "us"

    @field_validator("color_scheme", mode="before")
    @classmethod
    def _validate_scheme(cls, v: Any) -> str:
        s = (v or "cn").strip().lower()
        return s if s in ("cn", "us") else "cn"


class WechatConfig(BaseModel, frozen=True):
    """WeChat Open Platform OAuth configuration."""

    app_id: str = ""
    app_secret: str = ""
    redirect_uri: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.app_id.strip())


class QmtConfig(BaseModel, frozen=True):
    """QMT (迅投) execution configuration."""

    account_id: str = ""
    qmt_path: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.account_id.strip())


class ThsConfig(BaseModel, frozen=True):
    """TongHuaShun (同花顺) provider configuration."""

    username: str = ""
    password: str = ""

    @property
    def has_credentials(self) -> bool:
        return bool((self.username or "").strip() and (self.password or "").strip())


