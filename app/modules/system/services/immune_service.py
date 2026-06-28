from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Strategy Immune System: Automated self-healing for trading strategies."""


from typing import Any
from app.core.logger import get_logger
from app.modules.system.services.sentinel.sentinel_service import SentinelService

logger = get_logger(__name__)

class StrategyImmuneService:
    """Detects strategy failure and proactively generates recovery patches."""

    def __init__(
        self,
        sentinel: SentinelService | None = None,
        runtime: object = None,
    ):
        self.sentinel = sentinel or SentinelService()
        if runtime is not None:
            self._runtime = runtime
        else:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            from app.domain.ports.agent_ports import SwarmOrchestratorPort
            self._runtime = resolve_optional_service(SwarmOrchestratorPort)
        if self._runtime is None:
            from app.modules.system.services.helpers.agent_access import create_default_swarm_runtime
            self._runtime = create_default_swarm_runtime()

    def process_strategy_failure(self, strategy_id: str, diagnostics: dict[str, Any]) -> GenericResponseDTO:
        """Automatically analyze failure and patch the strategy."""
        logger.warning(f"Immune System activated for strategy {strategy_id}")

        run = self._runtime.start_run(
            preset_name="red_teaming_swarm",
            user_vars={"strategy_id": strategy_id, "diagnostics": str(diagnostics)}
        )

        return {
            "status": "remediating",
            "run_id": run.id,
            "message": "Auto-remediation swarm triggered"
        }
