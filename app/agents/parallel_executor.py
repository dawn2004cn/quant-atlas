from __future__ import annotations
"""Parallel Agent Executor with Circuit Breaker Isolation.

This module implements the Parallelism & Resilience from midify_plan9.md:
- ParallelAgentExecutor: Run agents concurrently with asyncio
- AgentCircuitBreaker: Isolate failing agents
- Graceful degradation when agents fail
"""


import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable

from ..core.resilience import CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker_registry

from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class AgentExecutionResult:
    """Result from a single agent execution."""
    agent_name: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    was_circuit_breaker: bool = False


class ParallelAgentExecutor:
    """Execute multiple agents in parallel with circuit breaker protection.

    This replaces sequential execution with concurrent execution,
    reducing end-to-end latency significantly.
    """

    def __init__(self, default_timeout: float = 30.0):
        self._default_timeout = default_timeout
        self._circuit_registry = get_circuit_breaker_registry()

    async def execute_agents(
        self,
        agents: list[tuple[str, Callable]],
        context: dict[str, Any],
        timeout: float | None = None,
        fail_silently: bool = True,
    ) -> list[AgentExecutionResult]:
        """Execute multiple agents in parallel.

        Args:
            agents: List of (agent_name, agent_function) tuples
            context: Context to pass to each agent
            timeout: Maximum time for all agents to complete
            fail_silently: If True, failed agents don't stop others

        Returns:
            List of AgentExecutionResult
        """
        timeout = timeout or self._default_timeout
        start_time = time.time()

        tasks = []
        for agent_name, agent_func in agents:
            task = self._execute_single_agent(
                agent_name,
                agent_func,
                context,
            )
            tasks.append(task)

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=not fail_silently),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Agent execution timed out after {timeout}s")
            results = [
                AgentExecutionResult(
                    agent_name=name,
                    success=False,
                    error="Timeout",
                    execution_time_ms=timeout * 1000,
                )
                for name, _ in agents
            ]

        return results

    async def _execute_single_agent(
        self,
        agent_name: str,
        agent_func: Callable,
        context: dict[str, Any],
    ) -> AgentExecutionResult:
        """Execute a single agent with circuit breaker."""
        start_time = time.time()

        breaker = self._circuit_registry.get_or_create(
            f"agent_{agent_name}",
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=30.0,
            ),
        )

        try:
            if not breaker.can_execute():
                logger.warning(f"Circuit breaker OPEN for {agent_name}, using fallback")
                return AgentExecutionResult(
                    agent_name=agent_name,
                    success=False,
                    error="Circuit breaker open",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    was_circuit_breaker=True,
                )

            result = await asyncio.to_thread(agent_func, context)

            breaker.record_success()

            return AgentExecutionResult(
                agent_name=agent_name,
                success=True,
                result=result,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            breaker.record_failure(e)
            logger.error(f"Agent {agent_name} failed: {e}")

            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )


class AgentCircuitBreaker:
    """Circuit breaker wrapper for individual agents.

    Provides isolation so that one failing agent doesn't
    block the entire analysis.
    """

    def __init__(self, agent_name: str, config: CircuitBreakerConfig | None = None):
        self._agent_name = agent_name
        self._breaker = CircuitBreaker(
            name=f"agent_{agent_name}",
            config=config or CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=30.0,
            ),
        )

    @property
    def is_available(self) -> bool:
        """Check if agent can be invoked."""
        return self._breaker.can_execute()

    @property
    def status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return self._breaker.get_status()

    def execute(self, func: Callable, fallback: Callable | None = None) -> Any:
        """Execute function with circuit breaker protection."""
        try:
            return self._breaker.execute(func, fallback)
        except Exception as e:
            if fallback:
                return fallback()
            raise

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._breaker.reset()


class ResilientAgentWrapper:
    """Wrapper that adds resilience to any agent function.

    Usage:
        wrapped = ResilientAgentWrapper(my_agent_function)
        result = await wrapped.execute(context)
    """

    def __init__(self, agent_name: str, timeout: float = 30.0):
        self._agent_name = agent_name
        self._timeout = timeout
        self._circuit_breaker = AgentCircuitBreaker(agent_name)

    async def execute(
        self,
        agent_func: Callable,
        context: dict[str, Any],
        fallback_result: Any | None = None,
    ) -> Any:
        """Execute agent with resilience."""
        if not self._circuit_breaker.is_available:
            logger.warning(f"Agent {self._agent_name} unavailable, using fallback")
            return fallback_result

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(agent_func, context),
                timeout=self._timeout,
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"Agent {self._agent_name} timed out")
            self._circuit_breaker._breaker.record_failure(Exception("Timeout"))
            return fallback_result

        except Exception as e:
            logger.error(f"Agent {self._agent_name} failed: {e}")
            self._circuit_breaker._breaker.record_failure(e)
            return fallback_result

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_name": self._agent_name,
            "available": self._circuit_breaker.is_available,
            "circuit_breaker": self._circuit_breaker.status,
        }


_global_executor: ParallelAgentExecutor | None = None


def get_parallel_executor() -> ParallelAgentExecutor:
    """Get the global parallel executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = ParallelAgentExecutor()
    return _global_executor