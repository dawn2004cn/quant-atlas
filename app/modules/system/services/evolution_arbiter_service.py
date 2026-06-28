"""Evolution Arbiter service — autonomous strategy evolution via champion/challenger mesh."""
from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.domain.evolution_arbiter import (
    EvolutionState,
    Regime,
    RegimeSnapshot,
)

logger = get_logger(__name__)


class EvolutionArbiterService:
    """Lightweight autonomous evolution loop.

    - detect regime via MetaArbiter verdicts
    - spin challengers through SimulationGateway
    - promote champion if challenger outperforms
    """

    def __init__(
        self,
        *,
        meta_arbiter_service: Any | None = None,
        simulation_gateway_service: Any | None = None,
    ) -> None:
        self._meta = meta_arbiter_service
        self._sim = simulation_gateway_service
        self._state = EvolutionState()

    def detect_regime(self, symbol: str = "000001", market: str = "CN") -> RegimeSnapshot:
        if self._meta is None:
            return RegimeSnapshot(regime=Regime.UNKNOWN, confidence=0.0, source="unavailable")
        try:
            verdict = self._meta.synthesize(symbol)
            verdict_text = str(verdict).lower()
            confidence = 0.55
            regime = Regime.UNKNOWN
            if "bull" in verdict_text:
                regime = Regime.BULL_STRONG if "strong" in verdict_text else Regime.BULL_WEAK
            elif "bear" in verdict_text:
                regime = Regime.BEAR_STRONG if "strong" in verdict_text else Regime.BEAR_WEAK
            elif "range" in verdict_text or "ranging" in verdict_text:
                regime = Regime.RANGING
            elif "volatil" in verdict_text:
                regime = Regime.VOLATILE
            return RegimeSnapshot(regime=regime, confidence=confidence, source="meta_arbiter")
        except Exception as exc:  # noqa: BLE001
            logger.debug("regime detection failed: %s", exc)
            return RegimeSnapshot(regime=Regime.UNKNOWN, confidence=0.0, source="error")

    def get_status(self) -> dict[str, Any]:
        return {
            "current_regime": self._state.current_regime.value,
            "champion": self._state.champion.model_dump(mode="json") if self._state.champion else None,
            "challenger_count": len(self._state.challengers),
            "evolution_count": self._state.evolution_count,
            "last_evolution_at": self._state.last_evolution_at.isoformat() if self._state.last_evolution_at else None,
        }
