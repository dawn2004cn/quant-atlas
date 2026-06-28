'''Auto-instrumentation middleware for route handlers, DB calls, and service methods.'''
from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

def instrument_service(call_type: str = "service"):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                _record_service(call_type, func.__name__, time.perf_counter() - start, True)
                return result
            except Exception:
                _record_service(call_type, func.__name__, time.perf_counter() - start, False)
                raise
        return wrapper
    return decorator

def _record_service(call_type: str, method: str, duration: float, success: bool):
    try:
        from app.core.metrics import ERROR_COUNT, FACADE_CALL_DURATION
        if not success and ERROR_COUNT is not None:
            ERROR_COUNT.labels(error_type=f"service_{call_type}", endpoint=method).inc()
        if FACADE_CALL_DURATION is not None:
            FACADE_CALL_DURATION.labels(facade=call_type, method=method).observe(duration)
    except Exception:
        pass

def get_service_metrics_snapshot() -> dict[str, Any]:
    return {"instrumented_types": ["service", "ai_analysis", "backtest", "sync", "market_data"], "active": True}
