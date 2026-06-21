from __future__ import annotations

"""Profile-aware runtime configuration validation at bootstrap."""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.bootstrap_components.service_readiness import is_strict_bootstrap

logger = logging.getLogger(__name__)

_MYSQL_URI_PATTERN = re.compile(r"^mysql(\+[\w]+)?://", re.IGNORECASE)
_VALID_PROFILES = frozenset({"dev", "prod", "production", "trading"})


@dataclass(frozen=True)
class RuntimeConfigReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    profile: str
    fail_fast: bool

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_fail_fast(self) -> None:
        if self.fail_fast and self.errors:
            raise RuntimeError(
                "Runtime configuration validation failed: " + "; ".join(self.errors)
            )


def resolve_deploy_profile() -> str:
    raw = (os.environ.get("DEPLOY_PROFILE", "dev") or "dev").strip().lower()
    return raw if raw in _VALID_PROFILES else "dev"


def should_fail_fast_config(*, strict: bool | None = None, profile: str | None = None) -> bool:
    if strict is None:
        strict = is_strict_bootstrap()
    if strict:
        return True
    resolved = profile or resolve_deploy_profile()
    return resolved in ("prod", "production", "trading")


def validate_runtime_config(
    settings: Any,
    *,
    strict: bool | None = None,
    profile: str | None = None,
) -> RuntimeConfigReport:
    """Validate env-backed settings; fail fast when STRICT or prod/trading profile."""
    resolved_profile = profile or resolve_deploy_profile()
    fail_fast = should_fail_fast_config(strict=strict, profile=resolved_profile)

    errors: list[str] = []
    warnings: list[str] = []

    def _issue(code: str, *, force_error: bool = False) -> None:
        if fail_fast or force_error:
            errors.append(code)
        else:
            warnings.append(code)

    if getattr(settings, "use_mysql", False):
        mysql = getattr(settings, "mysql", None)
        if mysql is None:
            _issue("mysql_settings_missing")
        else:
            if not (mysql.host or "").strip():
                _issue("mysql_host_required")
            if not (mysql.database or "").strip():
                _issue("mysql_database_required")
            if not (mysql.user or "").strip():
                _issue("mysql_user_required")

        database_uri = (getattr(settings, "database_uri", "") or "").strip()
        if not database_uri:
            _issue("database_uri_required")
        elif not _MYSQL_URI_PATTERN.match(database_uri):
            _issue("database_uri_invalid_mysql_scheme")
        else:
            parsed = urlparse(database_uri)
            if not parsed.hostname or not parsed.path.strip("/"):
                _issue("database_uri_missing_host_or_database")

    if getattr(settings, "enable_celery", False):
        broker = (getattr(settings, "celery_broker_url", "") or "").strip()
        if not broker:
            _issue("celery_broker_url_required")

    qmt = getattr(settings, "qmt", None)
    if qmt is not None and qmt.enabled:
        qmt_path = (qmt.qmt_path or "").strip()
        if not qmt_path:
            _issue("qmt_path_required", force_error=resolved_profile == "trading")
        elif not Path(qmt_path).exists():
            _issue(
                f"qmt_path_not_found:{qmt_path}",
                force_error=resolved_profile == "trading",
            )

    if resolved_profile == "trading" and (qmt is None or not qmt.enabled):
        _issue("trading_profile_requires_qmt_account")

    tdx_root = (getattr(settings, "tdx_root_path", None) or "").strip()
    if tdx_root and not Path(tdx_root).exists():
        _issue("tdx_root_path_not_found")

    if warnings:
        logger.warning("Runtime config warnings (%s): %s", resolved_profile, "; ".join(warnings))
    if errors:
        logger.error("Runtime config errors (%s): %s", resolved_profile, "; ".join(errors))

    report = RuntimeConfigReport(
        errors=tuple(errors),
        warnings=tuple(warnings),
        profile=resolved_profile,
        fail_fast=fail_fast,
    )
    report.raise_if_fail_fast()
    return report


def validate_worker_runtime_config(*, strict: bool | None = None) -> RuntimeConfigReport | None:
    """Validate worker settings; only fail-fast when STRICT_BOOTSTRAP is enabled."""
    if strict is None:
        strict = is_strict_bootstrap()
    if not strict:
        return None

    from app.config import get_settings

    return validate_runtime_config(get_settings(), strict=True)
