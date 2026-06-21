from __future__ import annotations
"""Base service class for application services."""


import functools
import threading
from typing import Any, Callable, Awaitable
from functools import wraps

from app.core.logger import get_logger

logger = get_logger(__name__)

_audit_service: Any = None
_audit_lock = threading.Lock()


def set_audit_service(service):
    """Set the global audit service for @audit decorator."""
    global _audit_service
    with _audit_lock:
        _audit_service = service


def audit(action: str, target_type: str = "", include_args: bool = False):
    """Decorator to automatically log method calls to audit trail.

    Usage:
        class MyService(BaseApplicationService):
            @audit(action="buy_stock", target_type="trade")
            def execute_trade(self, user_id, symbol, quantity):
                ...

    Args:
        action: The action name to record (e.g., "buy_stock", "delete_position")
        target_type: The type of target (e.g., "trade", "position", "user")
        include_args: Whether to include method arguments in metadata
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            user_id = kwargs.get("user_id") or (args[0] if args else "system")
            metadata = {}
            if include_args:
                metadata["args"] = str(args)[:200]
                metadata["kwargs"] = {k: str(v)[:100] for k, v in list(kwargs.items())[:5]}

            try:
                result = func(self, *args, **kwargs)
                metadata["status"] = "success"

                if _audit_service:
                    try:
                        _audit_service.record(
                            user_id=user_id,
                            action=action,
                            target_type=target_type,
                            target_id=kwargs.get("symbol") or kwargs.get("stock_code") or "",
                            metadata=metadata
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record audit: {e}")

                return result
            except Exception as e:
                metadata["status"] = "failed"
                metadata["error"] = str(e)[:200]

                if _audit_service:
                    try:
                        _audit_service.record(
                            user_id=user_id,
                            action=action,
                            target_type=target_type,
                            target_id=kwargs.get("symbol") or kwargs.get("stock_code") or "",
                            metadata=metadata
                        )
                    except Exception as e:
                        logger.warning("base.py.audit: %s", e)
                raise
        return wrapper
    return decorator


def async_task(func: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
    """Decorator to run async service methods from sync callers (delegates to ``run_async``)."""
    from app.application.request_executor import run_async

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        return run_async(func(*args, **kwargs))

    return sync_wrapper


class BaseApplicationService:
    """Base class for all application services.
    
    Provides common functionality like logging and async HTTP client access.
    """
    
    def __init__(self, logger_name: str | None = None):
        self._logger = get_logger(logger_name or self.__class__.__name__)
    
    @property
    def logger(self):
        return self._logger
