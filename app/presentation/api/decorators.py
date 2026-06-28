from __future__ import annotations

"""Cross-cutting concerns: role decorators and exception wrappers.

Provides standardized decorators for:
- Role-based access control
- Exception wrapping for API responses
"""


import functools
import traceback
from collections.abc import Callable
from typing import Any

from flask import Response
from flask_login import current_user

from app.application.errors import ApplicationError, ExternalServiceError, ValidationError
from app.core.logger import get_logger
from app.presentation.api.common import ok_response

logger = get_logger(__name__)


class RoleChecker:
    """Centralized role checking utilities."""

    @staticmethod
    def check(method_name: str, error_msg: str = "Unauthorized") -> None:
        """Check if current user has the specified role."""
        fn = getattr(current_user, method_name, None)
        if not callable(fn) or not fn():
            raise ValidationError(error_msg)

    @staticmethod
    def has_permission(method_name: str) -> bool:
        """Check if current user has the specified role, returning bool."""
        fn = getattr(current_user, method_name, None)
        return callable(fn) and fn()


def require_role(role_method: str, error_msg: str | None = None):
    """Decorator to require a specific role for endpoint access.

    Usage:
        @blueprint.get("/admin/action")
        @login_required
        @require_role("can_manage_users", "需要管理员权限")
        def admin_action():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            RoleChecker.check(role_method, error_msg or f"requires_{role_method}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*role_methods: str):
    """Decorator to require any of the specified roles.

    Usage:
        @blueprint.get("/action")
        @login_required
        @require_any_role("can_manage_users", "may_trigger_server_data_ingestion")
        def action():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not any(RoleChecker.has_permission(m) for m in role_methods):
                raise ValidationError("requires_one_of_admin_roles")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_roles(*role_methods: str):
    """Decorator to require all specified roles.

    Usage:
        @blueprint.get("/action")
        @login_required
        @require_all_roles("can_manage_users", "may_run_research_writes")
        def action():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not all(RoleChecker.has_permission(m) for m in role_methods):
                raise ValidationError("requires_all_specified_roles")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def wrap_api_errors(include_traceback: bool = False):
    """Decorator to wrap function errors in standardized API response.

    Usage:
        @blueprint.get("/endpoint")
        @login_required
        @wrap_api_errors()
        def endpoint():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ValidationError, ApplicationError):
                raise
            except Exception as exc:
                logger.exception("Error in %s", func.__name__)
                if include_traceback:
                    logger.debug(traceback.format_exc())
                raise ExternalServiceError(
                    "api_handler_failed",
                    details={"handler": func.__name__, "reason": str(exc)},
                ) from exc
        return wrapper
    return decorator


def handle_service_errors(service_name: str = "Service"):
    """Decorator to handle service-level errors with context.

    Usage:
        @blueprint.get("/action")
        @login_required
        @handle_service_errors("StockService")
        def action():
            stock_service.get_quote(...)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError:
                raise
            except AttributeError as e:
                if "service" in str(e).lower():
                    msg = f"{service_name}_not_available"
                    raise ValidationError(msg) from e
                raise
            except Exception as e:
                logger.exception(f"{service_name} error")
                msg = f"{service_name.lower()}_error: {e}"
                raise ValidationError(msg) from e
        return wrapper
    return decorator


def service_fallback(service_attr: str, *, auto_catch: bool = False):
    """Decorator: if the given service attribute is None, return a 503 JSON immediately.

    Two modes:

    1. Default (auto_catch=False) — requires the inner function to have a closure
       variable named ``ctx`` (or ``runtime``) with an ``enable_legacy_response_fields``
       attribute.  The decorator does ``getattr(ctx, service_attr, None)`` before
       calling the function.

    2. auto_catch=True — catches ``AttributeError`` from calling methods on None.
       Use when the service lookup uses ``runtime.svc`` (property) or
       ``getattr(runtime.ctx, ...)`` where the receiver isn't directly ``ctx``.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if auto_catch:
                try:
                    return func(*args, **kwargs)
                except AttributeError as e:
                    if "'NoneType' object has no attribute" in str(e):
                        return ok_response(
                            data={"available": False, "summary": "Service unavailable"},
                            legacy_alias_key=None,
                            enable_legacy_alias=False,
                        )
                    raise

            # Default mode: walk closure for ctx
            ctx = _find_ctx_in_closure(func)
            if ctx is not None:
                svc = getattr(ctx, service_attr, None)
                if svc is None:
                    return ok_response(
                        data={"available": False, "summary": "Service unavailable"},
                        legacy_alias_key=None,
                        enable_legacy_alias=getattr(ctx, "enable_legacy_response_fields", False),
                    )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _find_ctx_in_closure(func):
    """Walk ``__closure__`` to find an ``ApiV1Context``-like object."""
    if func.__closure__:
        for cell in func.__closure__:
            try:
                val = cell.cell_contents
                if hasattr(val, "enable_legacy_response_fields"):
                    return val
            except ValueError:
                continue
    return None


def log_api_call(logger_name: str | None = None):
    """Decorator to log API calls with timing and parameters.

    Usage:
        @blueprint.get("/action")
        @login_required
        @log_api_call("MyEndpoint")
        def action():
            ...
    """
    def decorator(func: Callable) -> Callable:
        log = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                log.debug(f"{func.__name__} completed in {elapsed:.1f}ms")
            except Exception:
                elapsed = (time.time() - start) * 1000
                log.exception(f"{func.__name__} failed after {elapsed:.1f}ms")
                raise
            return result
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 60, key_func: Callable | None = None):
    """Simple in-memory cache decorator for endpoint results.

    Usage:
        @blueprint.get("/stats")
        @login_required
        @cache_result(ttl_seconds=300)
        def get_stats():
            return expensive_computation()
    """
    _cache: dict[str, tuple[Any, float]] = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            key = key_func(*args, **kwargs) if key_func else func.__name__

            if key in _cache:
                result, expiry = _cache[key]
                if expiry > time.time():
                    return result

            result = func(*args, **kwargs)
            _cache[key] = (result, time.time() + ttl_seconds)
            return result
        return wrapper
    return decorator


# ── Demo endpoint tag ───────────────────────────────────────────────

def demo_endpoint(f):
    """Mark an endpoint as a demo. Adds ``X-Demo: true`` response header.

    Usage::

        @blueprint.post("/ai-hedge-fund/analyze")
        @demo_endpoint
        def analyze():
            ...

    The decorated function also gets ``_is_demo = True`` for introspection.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        result = f(*args, **kwargs)
        if isinstance(result, Response):
            result.headers["X-Demo"] = "true"
        return result
    wrapper._is_demo = True
    return wrapper
