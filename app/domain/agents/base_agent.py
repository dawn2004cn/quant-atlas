"""Base agent class — implements AgentPort with common infrastructure.

Phase 8.2: All agent implementations should inherit from ``BaseAgent``
to get:
- Standardized ``agent_name`` / ``agent_type`` attributes
- Error enrichment via ``_enrich_error()``
- Optional telemetry via ``AgentTelemetryPort``
- Standardized ``invoke()`` signature
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the unified platform.

    Subclasses implement ``_do_invoke()`` with agent-specific logic.
    The ``invoke()`` wrapper handles error enrichment, telemetry, and
    timing.

    Usage::

        class MyAgent(BaseAgent):
            agent_name = "my_agent"
            agent_type = "custom"

            async def _do_invoke(self, inputs, user_id, thread_id):
                # Agent-specific logic
                return {"ok": True, "data": {...}}

        agent = MyAgent(telemetry=telemetry_port)
        result = await agent.invoke({"ticker": "600519"}, user_id=42)
    """

    agent_name: str = ""
    agent_type: str = "custom"

    def __init__(self, telemetry: Any | None = None) -> None:
        """Initialize the base agent.

        Args:
            telemetry: Optional ``AgentTelemetryPort`` for observability.
        """
        self._telemetry = telemetry

    # ── Abstract ───────────────────────────────────────────────────────

    @abstractmethod
    async def _do_invoke(
        self,
        inputs: dict[str, Any],
        user_id: int,
        thread_id: str | None,
    ) -> dict[str, Any]:
        """Agent-specific invocation logic.

        Subclasses override this method.  Errors raised here will be
        caught and enriched by ``invoke()``.
        """

    # ── Public API ─────────────────────────────────────────────────────

    async def invoke(
        self,
        inputs: dict[str, Any],
        user_id: int = 0,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Standardized invocation with error enrichment and telemetry.

        Args:
            inputs: Agent-specific input parameters.
            user_id: Current user ID.
            thread_id: Conversation/session thread identifier.

        Returns:
            Dict with ``ok``, ``data``/``error``, ``latency_ms``,
            and ``invocation_id``.
        """
        start_ts = time.monotonic()
        invocation_id = f"{self.agent_name[:8]}_{id(self):x}"

        try:
            result = await self._do_invoke(inputs, user_id, thread_id)
            elapsed_ms = round((time.monotonic() - start_ts) * 1000)
            ok = result.get("ok", True)

            # Normalize result shape
            if "data" not in result and "error" not in result:
                result["data"] = result  # pass-through if no explicit data/error

            result.setdefault("ok", ok)
            result["latency_ms"] = elapsed_ms
            result["invocation_id"] = invocation_id

            # Telemetry
            if self._telemetry:
                try:
                    await self._telemetry.record_invocation(
                        agent_name=self.agent_name,
                        user_id=user_id,
                        input_tokens=result.get("input_tokens", 0),
                        output_tokens=result.get("output_tokens", 0),
                        latency_ms=elapsed_ms,
                        success=ok,
                        error=result.get("error") if not ok else None,
                    )
                except Exception:
                    logger.warning(
                        "Telemetry record failed for agent %s",
                        self.agent_name, exc_info=True,
                    )

            return result

        except Exception as exc:
            elapsed_ms = round((time.monotonic() - start_ts) * 1000)
            enriched = self._enrich_error(exc)

            result = {
                "ok": False,
                "error": enriched,
                "latency_ms": elapsed_ms,
                "invocation_id": invocation_id,
            }

            # Telemetry on failure
            if self._telemetry:
                try:
                    await self._telemetry.record_invocation(
                        agent_name=self.agent_name,
                        user_id=user_id,
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=elapsed_ms,
                        success=False,
                        error=enriched,
                    )
                except Exception:
                    logger.warning(
                        "Telemetry record failed for agent %s",
                        self.agent_name, exc_info=True,
                    )

            logger.warning(
                "Agent %s failed: %s (%dms)",
                self.agent_name, enriched, elapsed_ms,
            )
            return result

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _enrich_error(exc: Exception) -> str:
        """Map raw SDK exceptions to actionable Chinese error messages."""
        raw = (str(exc) or "").strip() or type(exc).__name__
        name = type(exc).__name__
        lower = raw.lower()
        bits: list[str] = []

        if "APIConnection" in name or "ConnectError" in name or "connection" in lower:
            bits.append("连接失败：无法连上大模型端点。请检查 OPENAI_BASE_URL / OLLAMA_HOST。")
        if "timeout" in lower or "timed out" in lower:
            bits.append("请求超时：可适当增大 agent 超时配置。")
        if "401" in raw or "403" in raw or "unauthorized" in lower:
            bits.append("鉴权失败：请检查 API Key 是否与端点所属平台一致。")
        if "rate limit" in lower or "too many requests" in lower:
            bits.append("速率限制：请求过于频繁，请稍后重试。")
        if "model" in lower and ("not found" in lower or "does not exist" in lower or "invalid" in lower):
            bits.append("模型不存在：请检查配置的 model_name。")

        if not bits:
            return raw
        return raw + "\n\n" + "\n".join(bits)
