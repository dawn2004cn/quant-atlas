import functools
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

def track_latency(metric_name: str):
    """Decorator to track execution latency of a function.

    Logs the duration of the function call in seconds.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                logger.info("PERF_METRIC: %s | duration: %.4fs", metric_name, duration)
        return wrapper
    return decorator
