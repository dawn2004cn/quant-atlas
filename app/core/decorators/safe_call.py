"""Safe-call decorator for failure-isolation scenarios.

Replaces repetitive ``try: ... except Exception`` boilerplate when you want
to catch any error, log it, and return a default value instead of propagating.

Usage::

    @safe_call(default={}, logger=get_logger(__name__), label="fetch_quotes")
    def get_quotes(symbols: list[str]) -> dict:
        return {s: fetch(s) for s in symbols}  # Exception → returns {}

This decorator is preferred over bare ``except Exception`` blocks for:
- Cache reads that may fail (return ``default`` on error)
- External API calls where failure is non-fatal
- Feature-flagged code paths that degrade gracefully
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from logging import Logger, getLogger
from typing import Any, TypeVar

_T = TypeVar("_T")


def safe_call(
    *,
    default: Any = None,
    logger: Logger | None = None,
    label: str = "operation",
    log_level: int = 30,  # WARNING
) -> Callable[[Callable[..., _T]], Callable[..., _T]]:
    """Decorator factory: wraps a function to catch all exceptions.

    Args:
        default: Value returned on exception (default ``None``).
        logger: Logger instance (defaults to ``getLogger(__name__)`` of caller).
        label: Human-readable label for log messages.
        log_level: Logging level for exception messages.
    """

    def decorator(func: Callable[..., _T]) -> Callable[..., _T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)  # type: ignore[return-value]
            except Exception as exc:
                _log = logger or getLogger(func.__module__)
                _log.log(log_level, "%s failed in %s: %s", label, func.__qualname__, exc)
                return default
        return wrapper  # type: ignore[return-value]
    return decorator
