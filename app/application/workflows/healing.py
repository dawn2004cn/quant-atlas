from __future__ import annotations

"""Auto-healing — configurable retry policy with backoff and circuit breaker.

Sits at the ``BaseWorkflow`` level, wrapping step handlers with
exponential backoff and stopping retries after a circuit-breaker
threshold is breached.
"""


import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker keyed by (workflow_type, step_name).

    Opens (stops retrying) after *threshold* consecutive failures
    within a *window* duration, and half-opens after *cooldown*.
    """

    OPEN = "open"
    HALF_OPEN = "half_open"
    CLOSED = "closed"

    def __init__(self, threshold: int = 5, window: int = 300, cooldown: int = 60) -> None:
        self._threshold = threshold
        self._window = window
        self._cooldown = cooldown
        self._failures: dict[str, list[datetime]] = defaultdict(list)
        self._state: dict[str, str] = defaultdict(lambda: self.CLOSED)
        self._opened_at: dict[str, datetime] = {}

    def record_success(self, key: str) -> None:
        self._failures[key].clear()
        self._state[key] = self.CLOSED

    def record_failure(self, key: str) -> None:
        now = datetime.now()
        self._failures[key].append(now)
        # Prune old failures outside the window.
        cutoff = now - timedelta(seconds=self._window)
        self._failures[key] = [f for f in self._failures[key] if f > cutoff]

        if len(self._failures[key]) >= self._threshold:
            self._state[key] = self.OPEN
            self._opened_at[key] = now
            logger.warning("Circuit breaker OPEN for %s (threshold=%d)", key, self._threshold)

    def allow_request(self, key: str) -> bool:
        state = self._state[key]
        if state == self.CLOSED:
            return True
        if state == self.OPEN:
            opened = self._opened_at.get(key)
            if opened and (datetime.now() - opened).total_seconds() > self._cooldown:
                self._state[key] = self.HALF_OPEN
                logger.info("Circuit breaker HALF_OPEN for %s", key)
                return True
            return False
        # HALF_OPEN: allow one request through.
        return True


class RetryPolicy:
    """Per-step retry configuration with exponential backoff.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts (default 3).
    base_delay_s : float
        Base delay in seconds (default 2.0).  Actual delay =
        ``base_delay_s * (backoff_factor ** attempt)``.
    backoff_factor : float
        Multiplier applied each attempt (default 2.0).
    max_delay_s : float
        Cap on delay (default 120.0).
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_s: float = 2.0,
        backoff_factor: float = 2.0,
        max_delay_s: float = 120.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self.backoff_factor = backoff_factor
        self.max_delay_s = max_delay_s

    def delay(self, attempt: int) -> float:
        return min(self.base_delay_s * (self.backoff_factor ** attempt), self.max_delay_s)


def with_retry(
    handler: Callable[..., Any],
    policy: RetryPolicy | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    breaker_key: str = "",
) -> Callable[..., Any]:
    """Wrap a step handler with retry + circuit breaker logic."""
    policy = policy or RetryPolicy()
    cb = circuit_breaker

    @wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if cb and breaker_key and not cb.allow_request(breaker_key):
            raise RuntimeError(f"Circuit breaker OPEN for {breaker_key}; request blocked")

        last_exc: Exception | None = None
        for attempt in range(policy.max_retries + 1):
            try:
                result = handler(*args, **kwargs)
                if cb and breaker_key:
                    cb.record_success(breaker_key)
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < policy.max_retries:
                    delay_s = policy.delay(attempt)
                    logger.warning(
                        "Retry %s attempt %d/%d failed: %s — waiting %.1fs",
                        breaker_key or handler.__name__,
                        attempt + 1,
                        policy.max_retries,
                        exc,
                        delay_s,
                    )
                    time.sleep(delay_s)

        if cb and breaker_key:
            cb.record_failure(breaker_key)

        raise last_exc  # type: ignore[misc]

    return wrapper


__all__ = ["RetryPolicy", "CircuitBreaker", "with_retry"]
