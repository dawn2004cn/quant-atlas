"""Structured logging with structlog — unified with stdlib handlers.

All application loggers (stdlib + structlog) share console + file handlers.
Levels are controlled via ``LOG_LEVEL``, ``LOG_SQL_LEVEL``, etc. in
``app.core.logging_config``.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog
except ImportError:
    structlog = None  # type: ignore[assignment]


def _inject_log_context(_logger_obj: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Attach request/user context for Loki/ELK-compatible structured logs."""
    try:
        from app.core.middleware.resilience import get_request_id, get_user_id

        request_id = get_request_id()
        if request_id:
            event_dict["request_id"] = request_id
        user_id = get_user_id()
        if user_id:
            event_dict["user_id"] = user_id
    except Exception:
        logging.getLogger(__name__).debug(
            "Failed to inject request context into log event",
            exc_info=True,
        )
    return event_dict


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    *,
    structured: bool = False,
    console_colors: bool | None = None,
) -> None:
    """Configure structlog + stdlib root logging (console + file)."""
    if structlog is None:
        return

    from pathlib import Path

    from app.config import INSTANCE_DIR
    from app.core.logging_config import resolve_console_colors

    resolved_log_file = log_file or str(INSTANCE_DIR / "app.log")
    Path(resolved_log_file).parent.mkdir(parents=True, exist_ok=True)

    level_no = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level_no)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _inject_log_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    use_colors = (
        console_colors
        if console_colors is not None
        else resolve_console_colors(structured=structured)
    )

    if structured:
        console_processor: Any = structlog.processors.JSONRenderer()
        file_processor: Any = structlog.processors.JSONRenderer()
    else:
        console_processor = structlog.dev.ConsoleRenderer(colors=use_colors)
        file_processor = structlog.dev.ConsoleRenderer(colors=False)

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=console_processor,
        foreign_pre_chain=shared_processors,
    )
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=file_processor,
        foreign_pre_chain=shared_processors,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_no)
    console_handler.setFormatter(console_formatter)

    file_handler = logging.FileHandler(resolved_log_file, encoding="utf-8")
    file_handler.setLevel(level_no)
    file_handler.setFormatter(file_formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a structlog logger backed by stdlib (same handlers as logging.getLogger)."""
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)
