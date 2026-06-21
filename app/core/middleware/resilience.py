from __future__ import annotations
"""Resilience infrastructure: Context tracking and circuit breaker."""


import contextvars
import time
import uuid
from functools import wraps
from typing import Any, Callable

from app.core.circuit_breaker import (
    CircuitBreaker as _CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError as _CircuitBreakerOpenError,
    CircuitState,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


class RequestContext:
    """Request context for tracking."""

    def __init__(self, request_id: str = ""):
        self.request_id = request_id or str(uuid.uuid4())
        self.trace_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.metadata: dict[str, Any] = {}

    def set(self, key: str, value: Any):
        """Set context value."""
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.metadata.get(key, default)

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time


_context_stack: contextvars.ContextVar[RequestContext] = contextvars.ContextVar(
    "request_context", default=None
)


def init_context(request_id: str = "") -> RequestContext:
    """Initialize request context."""
    ctx = RequestContext(request_id)
    _context_stack.set(ctx)
    request_id_var.set(ctx.request_id)
    trace_id_var.set(ctx.trace_id)
    try:
        from app.core.logger import set_request_id

        set_request_id(ctx.request_id)
    except Exception:
        logger.debug("set_request_id skipped", exc_info=True)
    logger.debug(f"Context initialized: {ctx.request_id}")
    return ctx


def get_context() -> RequestContext | None:
    """Get current request context."""
    return _context_stack.get()


def clear_context():
    """Clear request context."""
    _context_stack.set(None)
    request_id_var.set("")
    trace_id_var.set("")
    user_id_var.set("")
    try:
        from app.core.logger import set_request_id

        set_request_id(None)
    except Exception:
        logger.debug("clear request_id skipped", exc_info=True)


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get()


def get_trace_id() -> str:
    """Get current trace ID."""
    return trace_id_var.get()


def set_user_id(user_id: str):
    """Set user ID in context."""
    user_id_var.set(user_id)
    ctx = get_context()
    if ctx:
        ctx.set("user_id", user_id)


def get_user_id() -> str:
    """Get current user ID."""
    return user_id_var.get()


class ContextMiddleware:
    """Middleware for context management."""

    def __init__(self, app=None):
        self.app = app

    def __call__(self, environ, start_response):
        """Process request with context."""
        request_id = environ.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        init_context(request_id)

        try:
            return self.app(environ, start_response)
        finally:
            ctx = get_context()
            if ctx:
                logger.info(f"Request {ctx.request_id} completed in {ctx.elapsed():.3f}s")
            clear_context()


class CircuitBreaker:
    """Circuit breaker for service protection (delegates to canonical impl)."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self._breaker = _CircuitBreaker(
            name,
            CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout=recovery_timeout,
                success_threshold=half_open_max_calls,
            ),
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        return self._breaker.call(func, *args, **kwargs)

    def get_state(self) -> dict:
        """Get circuit breaker state."""
        s = self._breaker.get_status()
        return {
            "name": s["name"],
            "is_open": s["state"] == CircuitState.OPEN.value,
            "failures": s["failure_count"],
            "next_attempt": (s.get("last_failure") or 0) + self._breaker.config.timeout,
        }

    def reset(self):
        """Reset circuit breaker."""
        self._breaker = _CircuitBreaker(self.name, self._breaker.config)
        logger.info(f"CircuitBreaker '{self.name}' reset")


CircuitBreakerOpenError = _CircuitBreakerOpenError


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers."""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get(cls, name: str, **config) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, **config)
        return cls._breakers[name]

    @classmethod
    def get_all_states(cls) -> list[dict]:
        """Get all circuit breaker states."""
        return [breaker.get_state() for breaker in cls._breakers.values()]

    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()


def with_circuit_breaker(breaker_name: str, **breaker_config):
    """Decorator to add circuit breaker protection to a function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get(breaker_name, **breaker_config)
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


__all__ = [
    "RequestContext",
    "init_context",
    "get_context",
    "clear_context",
    "get_request_id",
    "get_trace_id",
    "set_user_id",
    "get_user_id",
    "ContextMiddleware",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
    "with_circuit_breaker",
]