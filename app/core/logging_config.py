"""Central logging level and handler configuration (env-driven)."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import INSTANCE_DIR
from app.core.runtime_config import get_runtime, get_runtime_bool

_DEFAULT_LOG_FILE = INSTANCE_DIR / "app.log"

# App-owned SQL trace channel (see db_manager.setup_db_monitoring).
SQL_LOGGER_NAME = "app.sql"

# Third-party loggers whose levels are tuned independently of LOG_LEVEL.
_THIRD_PARTY_LOGGERS: tuple[tuple[str, str], ...] = (
    ("urllib3", "LOG_URLLIB3_LEVEL"),
    ("requests", "LOG_REQUESTS_LEVEL"),
    ("werkzeug", "LOG_WERKZEUG_LEVEL"),
    ("yfinance", "LOG_YFINANCE_LEVEL"),
    ("OpenBB", "LOG_OPENBB_LEVEL"),
    ("sqlalchemy.engine", "LOG_SQL_LEVEL"),
    ("sqlalchemy.pool", "LOG_SQL_LEVEL"),
    ("sqlalchemy.orm", "LOG_SQL_LEVEL"),
)


@dataclass(frozen=True)
class LoggingSettings:
    """Resolved logging configuration from environment."""

    level: int
    sql_level: int
    file_path: Path
    structured: bool
    werkzeug_level: int
    enable_sql_trace: bool
    console_colors: bool


def resolve_console_colors(*, structured: bool) -> bool:
    """Whether console output should use ANSI level colors (never for JSON/file)."""
    if structured:
        return False
    raw = get_runtime("LOG_COLORS", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return sys.stdout.isatty()


def _parse_level(name: str, default: str = "INFO") -> int:
    token = (name or default).strip().upper()
    return getattr(logging, token, getattr(logging, default.upper(), logging.INFO))


def resolve_logging_settings() -> LoggingSettings:
    """Read logging knobs from env / runtime config."""
    level = _parse_level(get_runtime("LOG_LEVEL", "INFO"))
    enable_sql_trace = get_runtime_bool("LOG_SQL", False) or get_runtime_bool(
        "ENABLE_SQL_LOG", False
    )
    sql_default = "INFO" if enable_sql_trace else "WARNING"
    sql_level = _parse_level(get_runtime("LOG_SQL_LEVEL", sql_default), sql_default)
    werkzeug_env = get_runtime("LOG_WERKZEUG_LEVEL", "").strip()
    if werkzeug_env:
        werkzeug_level = _parse_level(werkzeug_env, "WARNING")
    elif level <= logging.INFO:
        werkzeug_level = logging.INFO
    else:
        werkzeug_level = logging.WARNING

    file_raw = get_runtime("LOG_FILE", str(_DEFAULT_LOG_FILE)).strip()
    file_path = Path(file_raw)
    if not file_path.is_absolute():
        from app.config import BASE_DIR

        file_path = BASE_DIR / file_path

    structured = get_runtime_bool("LOG_STRUCTURED", False)
    console_colors = resolve_console_colors(structured=structured)

    return LoggingSettings(
        level=level,
        sql_level=sql_level,
        file_path=file_path,
        structured=structured,
        werkzeug_level=werkzeug_level,
        enable_sql_trace=enable_sql_trace,
        console_colors=console_colors,
    )


def configure_third_party_loggers(settings: LoggingSettings) -> None:
    """Apply per-library log levels after root logging is configured."""
    defaults: dict[str, int] = {
        "urllib3": logging.WARNING,
        "requests": logging.WARNING,
        "werkzeug": settings.werkzeug_level,
        "yfinance": logging.CRITICAL + 1,
        "OpenBB": logging.WARNING,
        "sqlalchemy.engine": settings.sql_level,
        "sqlalchemy.pool": settings.sql_level,
        "sqlalchemy.orm": max(settings.sql_level, logging.WARNING),
    }
    for logger_name, env_key in _THIRD_PARTY_LOGGERS:
        env_val = get_runtime(env_key, "").strip()
        level = _parse_level(env_val) if env_val else defaults.get(logger_name, settings.level)
        logging.getLogger(logger_name).setLevel(level)

    sql_logger = logging.getLogger(SQL_LOGGER_NAME)
    sql_logger.setLevel(settings.sql_level)
    sql_logger.propagate = True


def install_global_exception_hooks() -> None:
    """Route uncaught exceptions and warnings module output into logging."""

    logging.captureWarnings(True)

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("app.uncaught").critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _excepthook


def logging_already_configured() -> bool:
    """Return True when root logging already has handlers (app setup_logging ran)."""
    return bool(logging.getLogger().handlers)


def reassert_logging_config() -> LoggingSettings:
    """Re-apply env-driven logging after third-party code clobbered root handlers."""
    from app.core.logger import setup_logging

    return setup_logging()


__all__ = [
    "LoggingSettings",
    "SQL_LOGGER_NAME",
    "configure_third_party_loggers",
    "install_global_exception_hooks",
    "logging_already_configured",
    "reassert_logging_config",
    "resolve_console_colors",
    "resolve_logging_settings",
]
