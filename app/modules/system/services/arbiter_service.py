from __future__ import annotations

"""Arbiter Service: Synthesizes swarm intelligence + EventBus debate consensus."""

from typing import Any

from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService
from app.modules.system.services.debate_arbiter_service import DebateArbiterService

logger = get_logger(__name__)


class SwarmArbiterService:
    """Orchestrates multiple swarms and synthesizes final decisions via debate bus."""

    def __init__(
        self,
        swarm_service: SwarmAgentService,
        debate_arbiter: DebateArbiterService | None = None,
    ) -> None:
        self.swarm_service = swarm_service
        self._debate_arbiter = debate_arbiter or DebateArbiterService()

    def arbitrate(
        self,
        symbol: str,
        swarm_ids: list[str],
        *,
        market: str = "CN",
        wait_for_debate_rounds: int = 0,
    ) -> GenericResponseDTO:
        """Run swarms and synthesize consensus from EventBus debate rounds."""
        sym = (symbol or "").strip().upper()
        if not sym:
            return {"ok": False, "error": "symbol_required"}

        participating: list[dict[str, Any]] = []
        for swarm_id in swarm_ids:
            run = self.swarm_service.start_research_swarm(
                symbol=sym,
                topic=f"Strategic view on {sym}",
                preset=swarm_id,
            )
            participating.append({"swarm": swarm_id, "run_id": run.get("id")})

        consensus = self._debate_arbiter.synthesize(
            sym,
            market,
            min_rounds=max(1, wait_for_debate_rounds),
        )
        logger.info(
            "Arbitration sym=%s swarms=%s verdict=%s rounds=%s",
            sym,
            len(swarm_ids),
            consensus.get("verdict"),
            consensus.get("rounds_used"),
        )
        return {
            "ok": True,
            "symbol": sym,
            "market": market.upper(),
            "participating_swarms": participating,
            "consensus": consensus,
            "status": "arbitration_complete" if consensus.get("ok") else "awaiting_debate_rounds",
        }

    def consensus_only(
        self,
        symbol: str,
        market: str = "CN",
        *,
        use_llm: bool = False,
    ) -> GenericResponseDTO:
        """Synthesize from buffered debate rounds without starting swarms."""
        return self._debate_arbiter.synthesize(symbol, market, use_llm=use_llm)
