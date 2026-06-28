from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.base_service import BaseApplicationService

logger = logging.getLogger(__name__)

@dataclass
class SopParameters:
    """The final parameters to be pushed to the Reflex Map."""
    stop_distance: float
    risk_multiplier: float
    trigger_price: float | None = None
    trigger_side: str | None = None
    trigger_qty: int = 100

class StrategySOPService(BaseApplicationService):
    """
    StrategySOPService (Standard Operating Procedure) translates AI intuitions
    and Market Regimes into concrete Fast-Path parameters.

    It prevents the AI from making 'emotional' or inconsistent parameter choices
    by forcing them through a predefined Strategy Archetype.
    """

    def __init__(self, market_regime_service: Any):
        super().__init__()
        self._regime_service = market_regime_service
        # Mapping of archetype name → handler method
        self._archetypes = {
            "conservative": self._sop_conservative,
            "aggressive": self._sop_aggressive,
            "mean_reversion": self._sop_mean_reversion,
        }
        # Per‑symbol overrides – users can pin an archetype to a ticker
        self._symbol_archetype: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public management API (used by the HTTP layer)
    # ------------------------------------------------------------------
    def set_archetype(self, symbol: str, archetype: str) -> None:
        """Assign a specific archetype to a symbol (persisted in‑memory)."""
        if archetype not in self._archetypes:
            raise ValueError(f"Unknown archetype: {archetype}")
        self._symbol_archetype[symbol] = archetype
        logger.debug("SOP archetype set: %s → %s", symbol, archetype)

    def get_archetype(self, symbol: str) -> str | None:
        """Return the archetype assigned to a symbol, or ``None`` if not set."""
        return self._symbol_archetype.get(symbol)

    def compute_reflex_params(
        self,
        symbol: str,
        ai_verdict: dict[str, Any],
        archetype: str = "conservative"
    ) -> SopParameters:
        """
        Main entry point: AI Verdict + Archetype -> FastPath Params.
        """
        # Resolve per‑symbol archetype overrides first
        if symbol in self._symbol_archetype:
            archetype = self._symbol_archetype[symbol]

        regime = self._regime_service.get_current_regime(symbol) if self._regime_service else "neutral"

        sop_fn = self._archetypes.get(archetype, self._sop_conservative)
        params = sop_fn(ai_verdict, regime)

        logger.info("SOP Applied [%s] for %s: Regime=%s, Archetype=%s -> Params=%s",
                    symbol, symbol, regime, archetype, params)
        return params

    def _sop_conservative(self, verdict: dict[str, Any], regime: str) -> SopParameters:
        """
        Conservative SOP: Priority is Capital Preservation.
        Tight stops, low risk multiplier.
        """
        # If AI is not highly confident, drastically reduce risk
        confidence = verdict.get("confidence", 0.5)
        risk_mult = 0.5 if confidence < 0.7 else 1.0

        # In volatile regimes, tighten the stop
        stop_dist = 0.015 if regime == "volatile" else 0.02

        return SopParameters(
            stop_distance=stop_dist,
            risk_multiplier=risk_mult,
            trigger_side=verdict.get("side", "buy"),
            trigger_price=verdict.get("target_price")
        )

    def _sop_aggressive(self, verdict: dict[str, Any], regime: str) -> SopParameters:
        """
        Aggressive SOP: Priority is Alpha Capture.
        Wider stops to avoid noise, higher risk.
        """
        risk_mult = 2.0 if verdict.get("confidence", 0.5) > 0.8 else 1.2
        stop_dist = 0.04 # Give the trade room to breathe

        return SopParameters(
            stop_distance=stop_dist,
            risk_multiplier=risk_mult,
            trigger_side=verdict.get("side", "buy"),
            trigger_price=verdict.get("target_price")
        )

    def _sop_mean_reversion(self, verdict: dict[str, Any], regime: str) -> SopParameters:
        """
        Mean Reversion SOP: Bet on the return to average.
        Very tight trigger, but modest risk.
        """
        # Only trade if regime is actually range-bound or mean-reverting
        if regime not in ("range", "mean_reverting"):
            # Fallback to conservative if regime doesn't match
            return self._sop_conservative(verdict, regime)

        return SopParameters(
            stop_distance=0.01,
            risk_multiplier=1.0,
            trigger_side=verdict.get("side", "buy"),
            trigger_price=verdict.get("target_price")
        )
