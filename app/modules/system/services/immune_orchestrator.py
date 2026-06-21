from __future__ import annotations
"""Immune System Orchestrator: Automates stress testing."""


import logging
from app.modules.system.services.alpha.factor_performance_engine import FactorPerformanceEngine
from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService


from app.core.logger import get_logger

logger = get_logger(__name__)

class ImmuneSystemOrchestrator:
    """Orchestrates periodic stress tests for high-performing strategies."""

    def __init__(self, factor_engine: FactorPerformanceEngine, swarm_service: SwarmAgentService):
        self.factor_engine = factor_engine
        self.swarm_service = swarm_service

    def run_scheduled_audit(self) -> list[dict[str, Any]]:
        """Audits high-performing factors."""
        # 1. Get weights
        weights = self.factor_engine.config_loader.get_config("factor_weights")
        high_perf_factors = [f for f, w in weights.items() if w > 1.2]
        
        results = []
        for factor in high_perf_factors:
            logger.info(f"Running automated stress test for factor: {factor}")
            # Trigger red-teaming
            run = self.swarm_service.start_research_swarm(
                symbol="ALL",
                topic=f"Stress test for factor: {factor}",
                preset="red_teaming_swarm"
            )
            results.append({"factor": factor, "run_id": run.get("id")})
        
        return results
