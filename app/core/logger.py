from __future__ import annotations
"""Centralized logging configuration with structured logging support.

Environment variables (see ``.env.example``):

- ``LOG_LEVEL`` — root/app log level (DEBUG/INFO/WARNING/ERROR)
- ``LOG_SQL`` / ``ENABLE_SQL_LOG`` — enable SQL trace + sqlalchemy.engine
- ``LOG_SQL_LEVEL`` — SQL trace and sqlalchemy log level
- ``LOG_FILE`` — log file path (default ``instance/app.log``)
- ``LOG_STRUCTURED`` — 1 for JSON lines, 0 for human-readable
- ``LOG_WERKZEUG_LEVEL`` — werkzeug access/error log level
- ``LOG_COLORS`` — 1/0 force console ANSI colors; default on when stdout is a TTY
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import INSTANCE_DIR
from app.core.logging_config import (
    LoggingSettings,
    SQL_LOGGER_NAME,
    configure_third_party_loggers,
    install_global_exception_hooks,
    resolve_logging_settings,
)

_DEFAULT_LOG_FILE = str(INSTANCE_DIR / "app.log")

_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET_COLOR = "\033[0m"

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

try:
    from app.core import structlogger
    from app.core.structlogger import (
        get_logger as _sl_get_logger,
        setup_logging as _sl_setup,
    )

    _USES_STRUCTLOG = structlogger.structlog is not None
except ImportError:
    _USES_STRUCTLOG = False


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if request_id := _request_id_var.get():
            log_data["request_id"] = request_id

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        import json

        return json.dumps(log_data, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with consistent formatting."""

    def __init__(self, *, use_colors: bool = False) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        if not self._use_colors:
            return line
        color = _LEVEL_COLORS.get(record.levelname, "")
        if not color:
            return line
        token = f"[{record.levelname}]"
        return line.replace(token, f"{color}{token}{_RESET_COLOR}", 1)


def _stdlib_setup_logging(
    log_file: str = _DEFAULT_LOG_FILE,
    level: int = logging.INFO,
    structured: bool = False,
    *,
    console_colors: bool = False,
) -> None:
    """Legacy stdlib-based logging setup (used when structlog is unavailable)."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    if structured:
        console_formatter: logging.Formatter = StructuredFormatter()
        file_formatter = StructuredFormatter()
    else:
        console_formatter = HumanReadableFormatter(use_colors=console_colors)
        file_formatter = HumanReadableFormatter(use_colors=False)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def setup_logging(
    log_file: str | None = None,
    level: int | None = None,
    structured: bool | None = None,
) -> LoggingSettings:
    """Configure global logging from environment (override args optional)."""
    settings = resolve_logging_settings()
    resolved_level = level if level is not None else settings.level
    resolved_file = log_file or str(settings.file_path)
    resolved_structured = structured if structured is not None else settings.structured

    if _USES_STRUCTLOG:
        level_str = logging.getLevelName(resolved_level)
        _sl_setup(
            level=str(level_str),
            log_file=resolved_file,
            structured=resolved_structured,
            console_colors=settings.console_colors,
        )
    else:
        _stdlib_setup_logging(
            log_file=resolved_file,
            level=resolved_level,
            structured=resolved_structured,
            console_colors=settings.console_colors,
        )

    configure_third_party_loggers(settings)
    install_global_exception_hooks()

    logging.getLogger(__name__).info(
        "Logging initialized level=%s sql_level=%s file=%s structured=%s",
        logging.getLevelName(resolved_level),
        logging.getLevelName(settings.sql_level),
        resolved_file,
        resolved_structured,
    )
    return settings


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance for a specific module."""
    if _USES_STRUCTLOG:
        return _sl_get_logger(name)  # type: ignore[return-value]
    return logging.getLogger(name)


def set_request_id(request_id: str | None) -> None:
    """Set request ID for structured logging."""
    _request_id_var.set(request_id)


# Re-export for convenience
__all__ = ["LoggingSettings", "get_logger", "set_request_id", "setup_logging"]
