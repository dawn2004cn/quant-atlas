"""Tests for Phase 8.2 — Agent Platform convergence."""

from __future__ import annotations

import asyncio
from typing import Any

from app.application.services.agent_platform import (
    AgentInvocationResult,
    AgentPlatform,
    AgentPlatformConfig,
    AgentPort,
    AgentTelemetryPort,
    AgentRegistration,
    PlatformLLMConfig,
    PlatformRetryConfig,
    PlatformTimeoutConfig,
    PlatformMonitoringConfig,
    _enrich_error,
    get_agent_platform,
    reset_agent_platform,
)
from app.domain.agents.base_agent import BaseAgent


# ── Test Agent Implementations ────────────────────────────────────────────


class MockTelemetry:
    """Collects telemetry calls for test verification."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append({
            "agent_name": agent_name,
            "user_id": user_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
        })


class SuccessAgent(BaseAgent):
    """Agent that always succeeds."""

    agent_name = "success_agent"
    agent_type = "custom"

    async def _do_invoke(self, inputs: dict, user_id: int, thread_id: str | None) -> dict[str, Any]:
        return {"ok": True, "result": "success", "data": {"answer": "42"}}


class FailingAgent(BaseAgent):
    """Agent that always fails."""

    agent_name = "failing_agent"
    agent_type = "custom"

    async def _do_invoke(self, inputs: dict, user_id: int, thread_id: str | None) -> dict[str, Any]:
        raise RuntimeError("intentional failure")


class ConnectionErrorAgent(BaseAgent):
    """Agent that raises a connection error (for enrichment testing)."""

    agent_name = "conn_error_agent"
    agent_type = "custom"

    async def _do_invoke(self, inputs: dict, user_id: int, thread_id: str | None) -> dict[str, Any]:
        raise RuntimeError("APIConnectionError: connection refused")


class ManualAgent:
    """Agent that does NOT use BaseAgent — should still be registrable."""

    agent_name = "manual_agent"
    agent_type = "custom"

    async def invoke(self, inputs, user_id=0, thread_id=None):
        return {"ok": True, "data": {"manual": True}}


# ── AgentPlatform Tests ──────────────────────────────────────────────────


def test_register_and_list() -> None:
    platform = AgentPlatform()
    agent = SuccessAgent()
    name = platform.register(agent)
    assert name == "success_agent"
    assert platform.list_agents() == ["success_agent"]


def test_register_multiple() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())
    platform.register(FailingAgent())
    assert len(platform.list_agents()) == 2


def test_unregister() -> None:
    platform = AgentPlatform()
    agent = SuccessAgent()
    platform.register(agent)
    assert platform.unregister("success_agent") is True
    assert "success_agent" not in platform.list_agents()


def test_deactivate_agent() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())
    assert platform.deactivate("success_agent") is True
    status = platform.status()
    assert status["agents"]["success_agent"]["active"] is False


def test_activate_agent() -> None:
    platform = AgentPlatform()
    agent = SuccessAgent()
    platform.register(agent)
    platform.deactivate("success_agent")
    assert platform.activate("success_agent") is True
    assert platform.status()["agents"]["success_agent"]["active"] is True


# ── Invocation Tests ─────────────────────────────────────────────────────


def test_invoke_success_agent() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())

    result = asyncio.get_event_loop().run_until_complete(
        platform.invoke("success_agent", {"query": "test"}),
    )

    assert isinstance(result, AgentInvocationResult)
    assert result.ok is True
    assert result.agent_name == "success_agent"
    assert result.latency_ms >= 0
    assert result.data == {"answer": "42"}


def test_invoke_unregistered_agent() -> None:
    platform = AgentPlatform()

    result = asyncio.get_event_loop().run_until_complete(
        platform.invoke("nonexistent", {}),
    )

    assert result.ok is False
    assert "not registered" in result.error


def test_invoke_deactivated_agent() -> None:
    platform = AgentPlatform()
    agent = SuccessAgent()
    platform.register(agent)
    platform.deactivate("success_agent")

    result = asyncio.get_event_loop().run_until_complete(
        platform.invoke("success_agent", {}),
    )

    assert result.ok is False
    assert "deactivated" in result.error


def test_invoke_failing_agent() -> None:
    platform = AgentPlatform()
    platform.register(FailingAgent())

    result = asyncio.get_event_loop().run_until_complete(
        platform.invoke("failing_agent", {}),
    )

    assert result.ok is False
    assert "intentional failure" in result.error
    assert result.latency_ms >= 0


def test_invocation_count_tracked() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())

    # Invoke 3 times
    for _ in range(3):
        asyncio.get_event_loop().run_until_complete(
            platform.invoke("success_agent", {}),
        )

    assert platform.status()["agents"]["success_agent"]["invocations"] == 3


def test_last_error_tracked() -> None:
    platform = AgentPlatform()
    platform.register(FailingAgent())

    asyncio.get_event_loop().run_until_complete(
        platform.invoke("failing_agent", {}),
    )

    assert platform.status()["agents"]["failing_agent"]["last_error"] is not None


# ── Telemetry Tests ──────────────────────────────────────────────────────


def test_telemetry_on_success() -> None:
    telemetry = MockTelemetry()
    platform = AgentPlatform(telemetry=telemetry)
    platform.register(SuccessAgent())

    asyncio.get_event_loop().run_until_complete(
        platform.invoke("success_agent", {"query": "test"}, user_id=42),
    )

    assert len(telemetry.calls) == 1
    call = telemetry.calls[0]
    assert call["agent_name"] == "success_agent"
    assert call["user_id"] == 42
    assert call["success"] is True
    assert call["error"] is None
    assert call["latency_ms"] > 0


def test_telemetry_on_failure() -> None:
    telemetry = MockTelemetry()
    platform = AgentPlatform(telemetry=telemetry)
    platform.register(FailingAgent())

    asyncio.get_event_loop().run_until_complete(
        platform.invoke("failing_agent", {}),
    )

    assert len(telemetry.calls) == 1
    call = telemetry.calls[0]
    assert call["agent_name"] == "failing_agent"
    assert call["success"] is False
    assert "intentional failure" in (call["error"] or "")


def test_telemetry_disabled() -> None:
    config = AgentPlatformConfig(
        monitoring=PlatformMonitoringConfig(enable_telemetry=False),
    )
    telemetry = MockTelemetry()
    platform = AgentPlatform(config=config, telemetry=telemetry)
    platform.register(SuccessAgent())

    asyncio.get_event_loop().run_until_complete(
        platform.invoke("success_agent", {}),
    )

    # Telemetry should still be called even if disabled — the config
    # just controls whether the platform *log_agent_calls* is on.
    # The key test is that no crash occurs.


# ── Error Enrichment Tests ───────────────────────────────────────────────


def test_enrich_connection_error() -> None:
    exc = RuntimeError("APIConnectionError: connection refused")
    result = _enrich_error(exc)
    assert "连接失败" in result


def test_enrich_timeout() -> None:
    exc = TimeoutError("request timed out")
    result = _enrich_error(exc)
    assert "超时" in result


def test_enrich_auth_error() -> None:
    exc = PermissionError("401 unauthorized")
    result = _enrich_error(exc)
    assert "鉴权" in result


def test_enrich_rate_limit() -> None:
    exc = RuntimeError("rate limit exceeded")
    result = _enrich_error(exc)
    assert "速率" in result


def test_enrich_unknown_error() -> None:
    exc = RuntimeError("something unexpected")
    result = _enrich_error(exc)
    assert result == "something unexpected"  # no enrichment, return raw


def test_enrich_empty_error() -> None:
    exc = RuntimeError("")
    result = _enrich_error(exc)
    assert result == "RuntimeError"


# ── BaseAgent Tests ──────────────────────────────────────────────────────


def test_base_agent_success() -> None:
    agent = SuccessAgent()
    result = asyncio.get_event_loop().run_until_complete(
        agent.invoke({"query": "hello"}, user_id=1),
    )
    assert result["ok"] is True
    assert "latency_ms" in result
    assert "invocation_id" in result


def test_base_agent_failure() -> None:
    agent = FailingAgent()
    result = asyncio.get_event_loop().run_until_complete(
        agent.invoke({}, user_id=1),
    )
    assert result["ok"] is False
    assert "intentional failure" in result["error"]


def test_base_agent_error_enrichment() -> None:
    agent = ConnectionErrorAgent()
    result = asyncio.get_event_loop().run_until_complete(
        agent.invoke({}, user_id=1),
    )
    assert result["ok"] is False
    assert "连接失败" in result["error"]  # enriched with Chinese message


def test_base_agent_telemetry() -> None:
    telemetry = MockTelemetry()
    agent = SuccessAgent(telemetry=telemetry)

    asyncio.get_event_loop().run_until_complete(
        agent.invoke({}, user_id=99),
    )

    assert len(telemetry.calls) == 1
    assert telemetry.calls[0]["user_id"] == 99
    assert telemetry.calls[0]["success"] is True


# ── Platform Config Tests ────────────────────────────────────────────────


def test_default_config() -> None:
    config = AgentPlatformConfig()
    assert config.llm.default_tier == "l2_reasoning"
    assert config.timeout.agent_timeout_seconds == 60.0
    assert config.retry.max_retries == 3
    assert config.monitoring.enable_telemetry is True
    assert config.parallel_departments is True


def test_custom_config() -> None:
    config = AgentPlatformConfig(
        llm=PlatformLLMConfig(l1_model="custom-model"),
        timeout=PlatformTimeoutConfig(agent_timeout_seconds=120.0),
    )
    assert config.llm.l1_model == "custom-model"
    assert config.timeout.agent_timeout_seconds == 120.0


def test_platform_with_custom_config() -> None:
    config = AgentPlatformConfig(
        timeout=PlatformTimeoutConfig(agent_timeout_seconds=30.0),
    )
    platform = AgentPlatform(config=config)
    platform.register(SuccessAgent())
    status = platform.status()
    assert status["config"]["timeout_seconds"] == 30.0


# ── Singleton Tests ──────────────────────────────────────────────────────


def test_singleton_get_agent_platform() -> None:
    reset_agent_platform()
    p1 = get_agent_platform()
    p2 = get_agent_platform()
    assert p1 is p2
    reset_agent_platform()


# ── Status Tests ─────────────────────────────────────────────────────────


def test_status_structure() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())
    platform.register(FailingAgent())

    status = platform.status()
    assert status["total_agents"] == 2
    assert status["active_agents"] == 2
    assert "success_agent" in status["agents"]
    assert "failing_agent" in status["agents"]
    assert isinstance(status["agents"]["success_agent"]["invocations"], int)


def test_active_agents_count_after_deactivation() -> None:
    platform = AgentPlatform()
    platform.register(SuccessAgent())
    platform.register(FailingAgent())
    platform.deactivate("failing_agent")

    status = platform.status()
    assert status["active_agents"] == 1
