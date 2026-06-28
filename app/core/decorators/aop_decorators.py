from __future__ import annotations

"""AOP decorators for cross-cutting concerns.

Provides decorators for logging, monitoring, tracing, and rate limiting.
"""


import functools
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def trace(func: Callable) -> Callable:
    """Decorator to add function tracing."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__qualname__

        logger.debug(f"TRACE: {func_name} started")

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"TRACE: {func_name} completed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"TRACE: {func_name} failed after {elapsed:.3f}s - {e}")
            raise

    return wrapper


def monitor_latency(threshold_ms: float = 1000):
    """Decorator to monitor function latency."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__qualname__

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                if elapsed_ms > threshold_ms:
                    logger.warning(
                        f"LATENCY: {func_name} took {elapsed_ms:.1f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

                return result
            except Exception:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(f"LATENCY: {func_name} failed after {elapsed_ms:.1f}ms")
                raise

        return wrapper
    return decorator


def log_error(func: Callable) -> Callable:
    """Decorator to log function errors."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__qualname__

        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"ERROR: {func_name} - {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise

    return wrapper


def retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff: float = 2.0):
    """Decorator to retry failed functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            current_delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"RETRY: {func_name} failed after {max_attempts} attempts")
                        raise

                    logger.warning(
                        f"RETRY: {func_name} attempt {attempt + 1}/{max_attempts} "
                        f"failed, retrying in {current_delay}s - {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 60, key_prefix: str = "", max_size: int = 256):
    """Decorator to cache function results with thread-safe LRU eviction."""
    cache: dict[str, tuple[Any, float]] = {}
    lock = threading.Lock()

    def _evict():
        if len(cache) > max_size:
            oldest = sorted(cache.items(), key=lambda x: x[1][1])[:len(cache) // 4]
            for k, _ in oldest:
                del cache[k]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            cache_key = f"{key_prefix}:{func_name}:{str(args)}:{str(kwargs)}"

            with lock:
                if cache_key in cache:
                    result, timestamp = cache[cache_key]
                    if time.time() - timestamp < ttl_seconds:
                        logger.debug(f"CACHE: {func_name} hit")
                        return result

            result = func(*args, **kwargs)

            with lock:
                cache[cache_key] = (result, time.time())
                _evict()
                logger.debug(f"CACHE: {func_name} miss")

            return result

        return wrapper
    return decorator


def deprecated(replacement: str = ""):
    """Decorator to mark deprecated functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"DEPRECATED: {func.__qualname__} is deprecated"
            if replacement:
                msg += f", use {replacement} instead"
            logger.warning(msg)

            import warnings
            warnings.warn(msg, DeprecationWarning, stacklevel=2)

            return func(*args, **kwargs)

        return wrapper
    return decorator


def timing(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        logger.info(f"TIMING: {func.__qualname__} took {elapsed:.4f}s")
        return result

    return wrapper


class PerformanceMonitor:
    """Context manager for performance monitoring."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        logger.debug(f"MONITOR: {self.operation_name} started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time

        if exc_type is None:
            logger.info(f"MONITOR: {self.operation_name} completed in {elapsed:.4f}s")
        else:
            logger.error(f"MONITOR: {self.operation_name} failed after {elapsed:.4f}s")


def validate_input(**validators):
    """Decorator to validate function input parameters."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__

            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"VALIDATION: {func_name} parameter '{param_name}' "
                            f"failed validation for value: {value}"
                        )

            return func(*args, **kwargs)

        return wrapper
    return decorator


def audit_log(action: str):
    """Decorator to add audit logging."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id", "unknown")

            logger.info(
                f"AUDIT: User '{user_id}' performed '{action}' "
                f"via {func.__qualname__}"
            )

            try:
                result = func(*args, **kwargs)
                logger.info(f"AUDIT: {action} completed successfully")
                return result
            except Exception as e:
                logger.error(f"AUDIT: {action} failed - {e}")
                raise

        return wrapper
    return decorator


def handle_errors(default_return=None, error_level: str = "error"):
    """Decorator to handle errors with default return value."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_level = logger.error if error_level == "error" else logger.warning
                log_level(f"ERROR: {func.__qualname__} - {type(e).__name__}: {e}")

                if default_return is not None:
                    return default_return() if callable(default_return) else default_return
                raise

        return wrapper
    return decorator


__all__ = [
    "trace",
    "monitor_latency",
    "log_error",
    "retry",
    "cache_result",
    "deprecated",
    "timing",
    "PerformanceMonitor",
    "validate_input",
    "audit_log",
    "handle_errors",
]
