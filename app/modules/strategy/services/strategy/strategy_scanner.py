from __future__ import annotations
"""Scanner Service: Automated strategy signal scanner."""


from typing import Any

from app.core.logger import get_logger
from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService

logger = get_logger(__name__)

class AutomatedStrategyScanner:
    """Monitors strategies and identifies potential trading signals."""

    def __init__(self, swarm_service: SwarmAgentService | None = None):
        self._swarm_service = swarm_service

    @property
    def swarm_service(self) -> SwarmAgentService:
        if self._swarm_service is None:
            from app.modules.system.services.helpers.agent_access import (
                create_expert_skill_port,
                create_swarm_orchestrator_port,
            )
            self._swarm_service = SwarmAgentService(
                swarm_port=create_swarm_orchestrator_port(),
                skill_port=create_expert_skill_port(),
            )
        return self._swarm_service

    def scan_strategies(self, symbol_list: list[str]) -> list[dict[str, Any]]:
        """Run strategy presets against a list of symbols."""
        results = []
        presets = self.swarm_service.swarm_port.list_presets()

        # Filter for strategy-related presets
        strategy_presets = [p for p in presets if "strategy" in p.lower()]

        logger.info(f"Scanning {len(strategy_presets)} strategies across {len(symbol_list)} symbols")

        for preset in strategy_presets:
            for symbol in symbol_list:
                # Run the swarm as an audit/scan
                res = self.swarm_service.start_research_swarm(
                    symbol=symbol,
                    topic=f"Scan for entry signals for {symbol} using strategy {preset}",
                    preset=preset
                )
                results.append({"preset": preset, "symbol": symbol, "run_id": res.get("id")})

        return results
