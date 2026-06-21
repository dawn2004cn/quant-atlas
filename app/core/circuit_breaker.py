from __future__ import annotations
"""Circuit Breaker pattern for external API resilience."""


import functools
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import collections


from app.core.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 2         # Successes to close
    timeout: float = 30.0             # Seconds before half-open
    excluded_exceptions: tuple = ()    # Exceptions that don't count
    # Adaptive tuning parameters (Phase 6)
    min_timeout: float = 5.0           # Shortest possible timeout
    max_timeout: float = 300.0         # Longest possible timeout
    min_failure_threshold: int = 2     # Most sensitive (open fast)
    max_failure_threshold: int = 20    # Most tolerant
    adapt_window: int = 50             # Number of recent calls to consider


class CircuitBreaker:
    """Circuit breaker for external API calls.

    Usage:
        breaker = CircuitBreaker("deepseek_api", failure_threshold=3, timeout=30)

        @breaker
        def call_deepseek(prompt):
            return requests.post(url, json={"prompt": prompt})
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()
        # Phase 6: adaptive + shadow
        self._recent_outcomes: collections.deque = collections.deque(maxlen=self.config.adapt_window)
        self._shadow_probe_function: Optional[Callable] = None

    def _adapt_params(self, succeeded: bool) -> None:
        """Tune timeout and failure_threshold based on recent success/failure history."""
        with self._lock:
            self._recent_outcomes.append(1 if succeeded else 0)
            if len(self._recent_outcomes) < 5:
                return  # not enough data yet

            recent = list(self._recent_outcomes)
            success_rate = sum(recent) / len(recent)

            # Adjust timeout: lower when healthy, raise when failing
            target_timeout = 10.0 if success_rate > 0.9 else (
                60.0 if success_rate > 0.7 else 120.0
            )
            self.config.timeout = max(
                self.config.min_timeout,
                min(self.config.max_timeout, target_timeout),
            )

            # Adjust failure_threshold: raise when healthy, lower when failing
            target_threshold = 10 if success_rate > 0.9 else (
                5 if success_rate > 0.7 else 3
            )
            self.config.failure_threshold = max(
                self.config.min_failure_threshold,
                min(self.config.max_failure_threshold, target_threshold),
            )

    def register_shadow_probe(self, probe_fn: Callable) -> None:
        """Register a lightweight health-probe function for shadow execution.

        The probe should be a fast, read-only call that verifies the downstream
        service is alive (e.g. a health-endpoint GET or a simple ping).
        """
        self._shadow_probe_function = probe_fn

    def shadow_probe(self) -> bool:
        """Attempt a shadow probe call without affecting the main circuit state.

        If the probe succeeds and the circuit is OPEN, transition to HALF_OPEN
        so the next real call can attempt recovery.

        Returns True if the probe succeeded, False otherwise.
        """
        if self._shadow_probe_function is None:
            return False
        try:
            self._shadow_probe_function()
        except Exception:
            logger.debug("Circuit %s shadow probe failed (service still down)", self.name)
            return False

        # Probe succeeded — if OPEN, advance to HALF_OPEN for recovery
        with self._lock:
            if self._state == CircuitState.OPEN:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "Circuit %s shadow probe succeeded; transitioned to HALF_OPEN",
                    self.name,
                )
        return True

    def call_with_fallback(
        self, func: Callable, fallback: Any = None, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute with circuit breaker, returning fallback on OPEN.

        When the circuit is OPEN, this method:
        1. Attempts a shadow probe (if registered) to check recovery.
        2. Returns the fallback value instead of raising.
        """
        if self.state == CircuitState.OPEN:
            self.shadow_probe()
            return fallback
        try:
            result = func(*args, **kwargs)
            self.record_success()
            self._adapt_params(succeeded=True)
            return result
        except CircuitBreakerOpenError:
            return fallback
        except Exception as e:
            self.record_failure(e)
            self._adapt_params(succeeded=False)
            if hasattr(self.config, "excluded_exceptions") and isinstance(e, self.config.excluded_exceptions):
                raise
            return fallback

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time and \
                   time.time() - self._last_failure_time > self.config.timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit {self.name} transitioned to HALF_OPEN")
            return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit {self.name} CLOSED after recovery")
        self._adapt_params(succeeded=True)

    def record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        if isinstance(exception, self.config.excluded_exceptions):
            return

        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(f"Circuit {self.name} OPEN after failure in half-open state")
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit {self.name} OPEN after {self._failure_count} failures")
        self._adapt_params(succeeded=False)

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def get_status(self) -> dict:
        """Get circuit breaker status with adaptive tuning info."""
        recent_list = list(self._recent_outcomes) if hasattr(self, "_recent_outcomes") else []
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time,
            "effective_timeout": getattr(self.config, "timeout", None),
            "effective_failure_threshold": getattr(self.config, "failure_threshold", None),
            "recent_success_rate": (
                round(sum(recent_list) / len(recent_list), 3)
                if recent_list else None
            ),
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _breakers: dict[str, CircuitBreaker] = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with cls._lock:
            if name not in cls._breakers:
                cls._breakers[name] = CircuitBreaker(name, config)
            return cls._breakers[name]

    @classmethod
    def get_all_status(cls) -> dict:
        """Get status of all circuit breakers."""
        return {name: b.get_status() for name, b in cls._breakers.items()}


# Decorator for easy use
def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 30.0
):
    """Decorator to add circuit breaker to a function.

    Usage:
        @circuit_breaker("openai_api", failure_threshold=3, timeout=60)
        def call_openai(prompt):
            return openai.Completion.create(prompt=prompt)
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        timeout=timeout
    )
    breaker = CircuitBreakerRegistry.get(name, config)

    def decorator(func: Callable) -> Callable:
        return breaker(func)

    return decorator


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
    "circuit_breaker",
]