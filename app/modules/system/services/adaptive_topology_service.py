"""Adaptive topology service — auto-switch research topology based on market regime (9.0 Swarm Morphing)."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.research.integrated_graph import build_integrated_research_graph
from app.modules.system.services.agent_topology_service import AgentTopologyService
from app.modules.system.services.topology_generator import TopologyGenerator
from app.core.event_bus import get_event_bus
from app.domain.events import ArbiterConsensusEvent, TruthDeviationEvent

logger = logging.getLogger(__name__)


class AdaptiveTopologyService:
    """Automatically select and switch research topology based on market regime.

    This service implements the "Swarm Morphing" concept from Quant Atlas 9.0:
    - Detects market regime (volatility, trend, crisis)
    - Generates appropriate topology via TopologyGenerator
    - Builds research graph with regime-optimized topology
    - Monitors for regime shifts and triggers topology switches
    """

    def __init__(
        self,
        *,
        topology_service: AgentTopologyService | None = None,
        topology_generator: TopologyGenerator | None = None,
    ) -> None:
        self._topology_service = topology_service or AgentTopologyService()
        self._generator = topology_generator or TopologyGenerator()
        self._current_regime: str | None = None
        self._current_topology_id: str | None = None
        self._event_bus = get_event_bus()
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Subscribe to events that may trigger topology switches."""
        self._event_bus.subscribe(TruthDeviationEvent, self._on_truth_deviation)
        self._event_bus.subscribe(ArbiterConsensusEvent, self._on_arbiter_consensus)

    def _on_truth_deviation(self, event: TruthDeviationEvent) -> None:
        """Handle truth deviation events — may indicate regime shift."""
        severity = event.payload.get("severity", "low")
        if severity in ("high", "critical"):
            logger.info(
                "Truth deviation detected (severity=%s), considering topology switch",
                severity,
            )
            self._current_regime = "crisis"
            self._current_topology_id = None

    def _on_arbiter_consensus(self, event: ArbiterConsensusEvent) -> None:
        """Handle arbiter consensus — may indicate stable regime."""
        confidence = event.payload.get("confidence", 0.0)
        if confidence > 0.8:
            logger.debug("High-confidence consensus detected, regime likely stable")

    def get_regime_for_symbol(self, symbol: str, market: str = "CN") -> str:
        """Detect market regime for a symbol.

        Returns one of: "high_volatility", "trending", "crisis", "low_volatility", "normal"
        """
        result = self._topology_service.compute_topology(symbol, market=market)
        regime = result.get("regime", "normal")

        regime_map = {
            "trending": "trending",
            "ranging": "low_volatility",
            "high_volatility": "high_volatility",
            "crisis": "crisis",
            "unknown": "normal",
        }

        return regime_map.get(regime, "normal")

    def build_adaptive_graph(
        self,
        llm: Any,
        symbol: str,
        market: str = "CN",
        *,
        checkpointer: Any = None,
        force_regime: str | None = None,
    ) -> Any:
        """Build a research graph with regime-adapted topology.

        Args:
            llm: Language model for agent execution
            symbol: Stock symbol to analyze
            market: Market code (e.g., "CN", "US")
            checkpointer: Optional LangGraph checkpointer
            force_regime: Override regime detection (for testing)

        Returns:
            Compiled LangGraph with regime-optimized topology
        """
        regime = force_regime or self.get_regime_for_symbol(symbol, market)

        if regime != self._current_regime:
            logger.info(
                "Regime shift detected for %s: %s -> %s, generating new topology",
                symbol,
                self._current_regime,
                regime,
            )
            self._current_regime = regime
            self._current_topology_id = None

        logger.info("Building research graph for %s with regime=%s", symbol, regime)

        graph = build_integrated_research_graph(
            llm,
            checkpointer=checkpointer,
            regime=regime,
            symbol=symbol,
        )

        self._current_topology_id = f"adaptive_{regime}_{symbol}"
        return graph

    def propose_topology_change(
        self,
        symbol: str,
        event_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Propose a topology change based on market events.

        Args:
            symbol: Stock symbol
            event_context: Event details (type, severity, etc.)

        Returns:
            Proposal with new topology and rationale
        """
        proposal = self._generator.propose_new_agent(event_context)

        if proposal.get("auto_apply"):
            regime = self.get_regime_for_symbol(symbol)
            new_topology = self._generator.generate_from_regime(regime, symbol=symbol)
            proposal["applied_topology"] = new_topology.model_dump()
            proposal["regime"] = regime
            logger.info(
                "Auto-applied topology change for %s: regime=%s",
                symbol,
                regime,
            )

        return proposal

    def get_current_state(self) -> dict[str, Any]:
        """Get current adaptive topology state."""
        return {
            "current_regime": self._current_regime,
            "current_topology_id": self._current_topology_id,
            "available_regimes": list(self._generator.list_regime_presets().keys()),
            "available_templates": len(self._generator.list_templates()),
        }


_adaptive_service: AdaptiveTopologyService | None = None


def get_adaptive_topology_service() -> AdaptiveTopologyService:
    """Get or create the global adaptive topology service instance."""
    global _adaptive_service
    if _adaptive_service is None:
        _adaptive_service = AdaptiveTopologyService()
    return _adaptive_service


__all__ = ["AdaptiveTopologyService", "get_adaptive_topology_service"]
