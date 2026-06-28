from __future__ import annotations

"""Circuit Breaker & Error Handling - Agent Resilience Framework.

This module implements from midify_plan13.md optimization:
- CircuitBreaker: Prevents cascading failures in agent pipeline
- AgentRetry: Automatic retry with exponential backoff
- ErrorBoundary: Catches and handles exceptions gracefully

Usage:
    breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=30)
    result = await breaker.execute(agent.execute)
"""


import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AgentRetry:
    """Retry configuration for agent execution."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        exponential_base: float = 2.0,
    ):
        self._max_retries = max_retries
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds
        self._exp_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff."""
        delay = self._base_delay * (self._exp_base ** attempt)
        return min(delay, self._max_delay)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Execute function with retry logic."""
        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    # Run synchronous functions in a thread to avoid blocking the event loop
                    return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self._max_retries:
                    delay = self.get_delay(attempt)
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)

        raise last_error


@dataclass
class CircuitBreaker:
    """Circuit breaker for agent execution.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Test if service recovered
    """

    failure_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 2

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        return (datetime.now() - self._last_failure_time).total_seconds() >= self.timeout_seconds

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened after half-open failure")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Failures: {self._failure_count}"
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class AgentErrorBoundary:
    """Error boundary for agent execution with fallback."""

    def __init__(
        self,
        fallback_response: str = "Analysis temporarily unavailable",
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self._fallback = fallback_response
        self._breaker = circuit_breaker or CircuitBreaker()

    async def execute_with_boundary(
        self,
        agent_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute with error boundary protection."""
        try:
            result = await self._breaker.execute(func, *args, **kwargs)

            if isinstance(result, dict):
                return result
            return {"success": True, "result": result, "agent": agent_name}

        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker open for {agent_name}: {e}")
            return {
                "success": False,
                "error": "circuit_breaker_open",
                "fallback": self._fallback,
                "agent": agent_name,
            }
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": self._fallback,
                "agent": agent_name,
            }


class AgentResilienceManager:
    """Manages resilience for all agents in the system."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._retry_configs: dict[str, AgentRetry] = {}

    def get_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for agent."""
        if agent_name not in self._breakers:
            self._breakers[agent_name] = CircuitBreaker()
        return self._breakers[agent_name]

    def get_retry(self, agent_name: str) -> AgentRetry:
        """Get or create retry config for agent."""
        if agent_name not in self._retry_configs:
            self._retry_configs[agent_name] = AgentRetry()
        return self._retry_configs[agent_name]

    def get_system_health(self) -> dict[str, Any]:
        """Get health status of all agents."""
        return {
            agent: {
                "state": breaker.state.value,
                "failure_count": breaker._failure_count,
            }
            for agent, breaker in self._breakers.items()
        }


_global_resilience_manager: AgentResilienceManager | None = None


def get_resilience_manager() -> AgentResilienceManager:
    """Get singleton resilience manager."""
    global _global_resilience_manager
    if _global_resilience_manager is None:
        _global_resilience_manager = AgentResilienceManager()
    return _global_resilience_manager
