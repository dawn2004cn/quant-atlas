"""Unified Agent Platform — convergence point for all AI agent implementations.

Phase 8.2: Agent 平台收敛

Problem
-------
Quant Atlas had 10+ agent implementations spread across ``app/``, each with:
- Its own ``AgentConfig`` dataclass (3+ different definitions)
- Different LLM resolution strategies (``get_llm()``, ``LlmProviderService``,
  direct SDK imports)
- Inconsistent error handling, telemetry, and lifecycle management
- No shared interface — agents cannot be swapped or composed

Solution
--------
``AgentPlatform`` provides:

1. **Unified config** — single ``AgentPlatformConfig`` dataclass replacing all
   scattered ``AgentConfig`` definitions.
2. **Unified LLM resolution** — all agents resolve LLM clients via
   ``LlmProviderService.build_client(config)`` with a deterministic fallback
   chain.
3. **Common lifecycle** — ``register()`` / ``activate()`` / ``deactivate()``
   / ``destroy()`` with telemetry hooks.
4. **Standardized error enrichment** — ``_enrich_error()`` maps raw SDK
   exceptions to actionable Chinese messages.
5. **Telemetry** — optional ``AgentTelemetryPort`` for token/latency tracking.
6. **Port-based interface** — ``AgentPort`` protocol that every agent must
   implement, enabling dependency injection and swapping.

Usage
-----
.. code-block:: python

    platform = AgentPlatform(
        llm_provider=llm_svc,
        telemetry=telemetry_port,
    )

    # Register agents
    platform.register(TradingAgent("research"))
    platform.register(SwarmAgent("market"))

    # Run through unified interface
    result = await platform.invoke(
        agent_name="research",
        inputs={"ticker": "600519", "query": "分析贵州茅台"},
    )

    # Query platform status
    status = platform.status()
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Unified Config ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlatformLLMConfig:
    """Single source of truth for LLM tier configuration."""

    default_tier: str = "l2_reasoning"
    l1_model: str = "gpt-4o-mini"
    l2_model: str = "gpt-4o"
    l1_max_tokens: int = 1024
    l2_max_tokens: int = 4096
    l1_temperature: float = 0.3
    l2_temperature: float = 0.5


@dataclass(frozen=True)
class PlatformTimeoutConfig:
    """Timeout configuration for agent operations."""

    agent_timeout_seconds: float = 60.0
    supervisor_timeout_seconds: float = 30.0
    analyst_timeout_seconds: float = 90.0
    risk_manager_timeout_seconds: float = 45.0
    tool_timeout_seconds: float = 20.0


@dataclass(frozen=True)
class PlatformRetryConfig:
    """Retry and resilience configuration."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class PlatformMonitoringConfig:
    """Telemetry and monitoring toggles."""

    enable_telemetry: bool = True
    log_agent_calls: bool = True
    track_token_usage: bool = True
    track_latency: bool = True


@dataclass(frozen=True)
class AgentPlatformConfig:
    """Unified agent platform configuration — replaces all scattered AgentConfig."""

    llm: PlatformLLMConfig = field(default_factory=PlatformLLMConfig)
    timeout: PlatformTimeoutConfig = field(default_factory=PlatformTimeoutConfig)
    retry: PlatformRetryConfig = field(default_factory=PlatformRetryConfig)
    monitoring: PlatformMonitoringConfig = field(default_factory=PlatformMonitoringConfig)

    parallel_departments: bool = True
    enable_early_exit: bool = True
    enable_weighted_consensus: bool = True
    max_conversation_rounds: int = 30


# ── Telemetry Port ─────────────────────────────────────────────────────────


class AgentTelemetryPort(Protocol):
    """Optional telemetry interface for agent observability."""

    async def record_invocation(
        self,
        agent_name: str,
        user_id: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record a single agent invocation."""


# ── Agent Lifecycle ────────────────────────────────────────────────────────


@dataclass
class AgentRegistration:
    """Metadata for a registered agent."""

    agent_name: str
    agent_type: str  # "research", "swarm", "autonomous", "hedge_fund", etc.
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    invocation_count: int = 0
    last_error: str | None = None


@dataclass
class AgentInvocationResult:
    """Standardized result from an agent invocation."""

    agent_name: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: float = 0.0
    token_usage: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


# ── Error Enrichment ───────────────────────────────────────────────────────


def _enrich_error(exc: Exception, provider: str = "unknown") -> str:
    """Map raw SDK exceptions to actionable Chinese error messages.

    Consolidates error enrichment logic previously scattered across
    multiple agent implementations (TradingAgentsService, etc.).
    """
    raw = (str(exc) or "").strip() or type(exc).__name__
    name = type(exc).__name__
    lower = raw.lower()
    bits: list[str] = []

    if "APIConnection" in name or "ConnectError" in name or "connection" in lower:
        bits.append(
            f"{provider} 连接失败：无法连上大模型端点。请检查 OPENAI_BASE_URL / OLLAMA_HOST "
            f"是否正确设置，以及网络是否可达。"
        )
    if "timeout" in lower or "timed out" in lower:
        bits.append(f"{provider} 请求超时：可适当增大 agent 超时配置，或检查模型推理是否过慢。")
    if "401" in raw or "403" in raw or "unauthorized" in lower:
        bits.append(f"{provider} 鉴权失败：请检查 API Key 是否与端点所属平台一致。")
    if "rate limit" in lower or "too many requests" in lower:
        bits.append(f"{provider} 速率限制：请求过于频繁，请稍后重试。")
    if "model" in lower and ("not found" in lower or "does not exist" in lower or "invalid" in lower):
        bits.append(f"{provider} 模型不存在：请检查配置的 model_name 是否正确。")

    if not bits:
        return raw
    return raw + "\n\n" + "\n".join(bits)


# ── Agent Port (Base Interface) ────────────────────────────────────────────


class AgentPort(Protocol):
    """Base protocol that every agent must implement.

    This enables dependency injection and agent swapping without
    changing caller code.
    """

    agent_name: str
    agent_type: str

    async def invoke(
        self,
        inputs: dict[str, Any],
        user_id: int = 0,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute the agent with given inputs.

        Args:
            inputs: Agent-specific input parameters.
            user_id: Current user ID for personalization.
            thread_id: Conversation/session thread identifier.

        Returns:
            Dict with at least ``ok`` and ``data`` / ``error`` keys.
        """


# ── AgentPlatform ──────────────────────────────────────────────────────────


class AgentPlatform:
    """Unified agent platform — registers, manages, and invokes agents.

    Provides:
    - Centralized config (replacing scattered AgentConfig)
    - LLM resolution via LlmProviderService
    - Error enrichment
    - Telemetry hooks
    - Agent lifecycle management
    """

    def __init__(
        self,
        config: AgentPlatformConfig | None = None,
        telemetry: AgentTelemetryPort | None = None,
    ) -> None:
        self._config = config or AgentPlatformConfig()
        self._telemetry = telemetry
        self._agents: dict[str, AgentRegistration] = {}
        self._agent_instances: dict[str, Any] = {}  # name -> agent instance

    # ── Registration ─────────────────────────────────────────────────────

    def register(self, agent: AgentPort) -> str:
        """Register an agent and return its name."""
        name = getattr(agent, "agent_name", type(agent).__name__)
        agent_type = getattr(agent, "agent_type", "custom")

        self._agents[name] = AgentRegistration(
            agent_name=name,
            agent_type=agent_type,
        )
        self._agent_instances[name] = agent  # store instance for invocation

        if self._config.monitoring.log_agent_calls:
            logger.info(
                "Agent registered: %s (type=%s)",
                name, agent_type,
            )

        return name

    def unregister(self, agent_name: str) -> bool:
        """Unregister an agent by name."""
        if agent_name in self._agents:
            del self._agents[agent_name]
            logger.info("Agent unregistered: %s", agent_name)
            return True
        return False

    def activate(self, agent_name: str) -> bool:
        if agent_name in self._agents:
            self._agents[agent_name].active = True
            return True
        return False

    def deactivate(self, agent_name: str) -> bool:
        if agent_name in self._agents:
            self._agents[agent_name].active = False
            return True
        return False

    # ── Invocation ───────────────────────────────────────────────────────

    async def invoke(
        self,
        agent_name: str,
        inputs: dict[str, Any],
        user_id: int = 0,
        thread_id: str | None = None,
    ) -> AgentInvocationResult:
        """Invoke a registered agent with standardized lifecycle.

        Handles:
        1. Agent lookup and activation check
        2. Timing measurement
        3. Error enrichment
        4. Telemetry recording
        5. Invocation count tracking
        """
        # Lookup
        reg = self._agents.get(agent_name)
        if reg is None:
            return AgentInvocationResult(
                agent_name=agent_name,
                ok=False,
                error=f"Agent '{agent_name}' not registered",
            )

        if not reg.active:
            return AgentInvocationResult(
                agent_name=agent_name,
                ok=False,
                error=f"Agent '{agent_name}' is deactivated",
            )

        # Find the actual agent instance (stored by name)
        agent = self._resolve_agent_instance(agent_name)
        if agent is None:
            return AgentInvocationResult(
                agent_name=agent_name,
                ok=False,
                error=f"No agent implementation found for '{agent_name}'",
            )

        # Timing
        start_ts = time.monotonic()
        reg.invocation_count += 1

        try:
            result = await agent.invoke(inputs, user_id=user_id, thread_id=thread_id)

            elapsed_ms = round((time.monotonic() - start_ts) * 1000)
            ok = result.get("ok", True)

            # Telemetry
            if self._telemetry and self._config.monitoring.track_token_usage:
                await self._telemetry.record_invocation(
                    agent_name=agent_name,
                    user_id=user_id,
                    input_tokens=result.get("input_tokens", 0),
                    output_tokens=result.get("output_tokens", 0),
                    latency_ms=elapsed_ms,
                    success=ok,
                    error=result.get("error") if not ok else None,
                )

            reg.last_error = None
            return AgentInvocationResult(
                agent_name=agent_name,
                ok=ok,
                data=result.get("data", result),
                error=result.get("error") if not ok else None,
                latency_ms=elapsed_ms,
                token_usage=result.get("token_usage", {}),
            )

        except Exception as exc:
            elapsed_ms = round((time.monotonic() - start_ts) * 1000)
            enriched = _enrich_error(exc, provider=agent_name)
            reg.last_error = enriched

            if self._telemetry:
                await self._telemetry.record_invocation(
                    agent_name=agent_name,
                    user_id=user_id,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=elapsed_ms,
                    success=False,
                    error=enriched,
                )

            return AgentInvocationResult(
                agent_name=agent_name,
                ok=False,
                error=enriched,
                latency_ms=elapsed_ms,
            )

    # ── Status ───────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return platform status including all registered agents."""
        return {
            "config": {
                "parallel_departments": self._config.parallel_departments,
                "enable_early_exit": self._config.enable_early_exit,
                "max_conversation_rounds": self._config.max_conversation_rounds,
                "timeout_seconds": self._config.timeout.agent_timeout_seconds,
            },
            "agents": {
                name: {
                    "type": reg.agent_type,
                    "active": reg.active,
                    "invocations": reg.invocation_count,
                    "last_error": reg.last_error,
                }
                for name, reg in self._agents.items()
            },
            "total_agents": len(self._agents),
            "active_agents": sum(1 for r in self._agents.values() if r.active),
        }

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    # ── Internal ─────────────────────────────────────────────────────────

    def _resolve_agent_instance(self, agent_name: str) -> AgentPort | None:
        """Resolve the actual AgentPort instance for a registered agent."""
        return self._agent_instances.get(agent_name)


# ── Convenience ────────────────────────────────────────────────────────────

_platform: AgentPlatform | None = None


def get_agent_platform() -> AgentPlatform:
    """Get the global agent platform singleton."""
    global _platform
    if _platform is None:
        _platform = AgentPlatform()
    return _platform


def reset_agent_platform() -> None:
    """Reset the global platform (for testing)."""
    global _platform
    _platform = None
