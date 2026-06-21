from __future__ import annotations
"""Correlation ID for Distributed Tracing.

This module provides a correlation ID system that tracks requests across
the entire application lifecycle, from signal generation to order execution.

Key features:
- Automatic correlation ID generation (UUID based)
- ContextVar-based global storage (thread/async safe)
- Automatic propagation through async calls
- Integration with logging and event bus

Usage:
    from app.application.correlation import (
        get_correlation_id,
        set_correlation_id,
        correlation_id_context,
        generate_correlation_id,
    )

    # Get current correlation ID (auto-created if not exists)
    cid = get_correlation_id()

    # Use context manager for scoped operations
    with correlation_id_context("my-operation") as cid:
        log.info("Operation with correlation")

    # Generate new correlation for new request
    cid = generate_correlation_id()

    # Pass correlation through async boundaries
    async def child_function():
        cid = get_correlation_id()  # Automatically inherited
"""


import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional, Generator


from app.core.logger import get_logger

logger = get_logger(__name__)

CONTEXT_VAR_NAME = "correlation_id"


_context_var: ContextVar[Optional[str]] = ContextVar(CONTEXT_VAR_NAME, default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Uses UUID4 for uniqueness. Format: 'qa-{uuid}'

    Returns:
        New correlation ID string
    """
    return f"qa-{uuid.uuid4().hex[:16]}"


def get_correlation_id() -> str:
    """Get the current correlation ID from context.

    If no correlation ID is set in the current context, generates
    a new one. This ensures every operation has a traceable ID.

    Returns:
        Current correlation ID
    """
    cid = _context_var.get()
    if cid is None:
        cid = generate_correlation_id()
        _context_var.set(cid)
        logger.debug(f"Auto-generated correlation ID: {cid}")
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: Correlation ID to set
    """
    _context_var.set(correlation_id)
    logger.debug(f"Set correlation ID: {correlation_id}")


def clear_correlation_id() -> None:
    """Clear the correlation ID from current context."""
    _context_var.set(None)
    logger.debug("Cleared correlation ID")


@contextmanager
def correlation_id_context(
    operation_name: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """Context manager for correlation ID scope.

    Creates a new correlation ID for this operation scope.
    Useful for tracking a complete workflow (e.g., signal -> order).

    Args:
        operation_name: Optional name for this operation
        correlation_id: Optional existing correlation ID to use

    Yields:
        Correlation ID for this scope

    Example:
        with correlation_id_context("execute_order") as cid:
            log.info(f"Starting order execution")
            await process_order()
    """
    cid = correlation_id or generate_correlation_id()
    if operation_name:
        cid = f"{cid}-{operation_name}"

    previous = _context_var.get()
    _context_var.set(cid)

    logger.debug(f"Entering correlation context: {cid}")
    try:
        yield cid
    finally:
        if previous is not None:
            _context_var.set(previous)
        else:
            _context_var.set(None)
        logger.debug(f"Exiting correlation context: {cid}")


class CorrelationContext:
    """Class-based correlation context for more complex scenarios."""

    def __init__(self, operation_name: str = ""):
        self.operation_name = operation_name
        self.correlation_id: Optional[str] = None

    def __enter__(self) -> "CorrelationContext":
        self.correlation_id = generate_correlation_id()
        if self.operation_name:
            self.correlation_id = f"{self.correlation_id}-{self.operation_name}"
        _context_var.set(self.correlation_id)
        logger.debug(f"CorrelationContext enter: {self.correlation_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _context_var.set(None)
        logger.debug(f"CorrelationContext exit: {self.correlation_id}")

    def __repr__(self) -> str:
        return f"CorrelationContext(correlation_id={self.correlation_id})"


class CorrelationLogger:
    """Logger wrapper that automatically adds correlation ID to all logs."""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _format_message(self, message: str) -> str:
        cid = get_correlation_id()
        return f"[{cid}] {message}"

    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(self._format_message(message), *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._logger.info(self._format_message(message), *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(self._format_message(message), *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(self._format_message(message), *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(self._format_message(message), *args, **kwargs)


def get_logger(name: str) -> CorrelationLogger:
    """Get a logger with correlation ID support.

    Args:
        name: Logger name

    Returns:
        CorrelationLogger instance
    """
    return CorrelationLogger(name)


__all__ = [
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "correlation_id_context",
    "CorrelationContext",
    "CorrelationLogger",
    "get_logger",
]