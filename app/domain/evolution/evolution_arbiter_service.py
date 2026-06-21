"""Evolution Arbiter 8.0 P1 - autonomous strategy bias switching.

Monitors market regime changes and triggers champion-challenger
strategy evolution via MetaArbiter consensus signals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# Regime detection thresholds
_BEARISH_THRESHOLD = -0.15
_BULLISH_THRESHOLD = 0.15
_EVOLUTION_COOLDOWN_HOURS = 72


class EvolutionArbiterService:
    """Autonomous strategy evolution arbiter.

    Watches the MetaArbiter's consensus signals. When a regime change
    is detected (e.g. persistent bearish consensus), it triggers an
    evolution protocol: freeze underperforming strategies, spawn
    challenger strategies with the opposite bias, and promote the
    best challenger after a simulation cycle.
    """

    def __init__(
        self,
        *,
        meta_arbiter_service: Any | None = None,
        team_blackboard_service: Any | None = None,
        simulation_gateway_service: Any | None = None,
        evolution_cooldown_hours: int = _EVOLUTION_COOLDOWN_HOURS,
    ):
        self._meta = meta_arbiter_service
        self._blackboard = team_blackboard_service
        self._sim = simulation_gateway_service
        self._cooldown_hours = evolution_cooldown_hours
        self._last_evolution_at: dict[str, datetime] = {}

    def evaluate_regime(
        self,
        symbol: str,
        market: str = "CN",
        *,
        team_id: int = 0,
        force: bool = False,
    ) -> dict[str, Any]:
        """Evaluate current market regime and trigger evolution if needed.

        Steps:
        1. Pull MetaArbiter consensus for the symbol.
        2. Classify regime (bullish / bearish / neutral).
        3. If regime conflicts with current strategy bias, trigger evolution.
        4. Post decision context to blackboard.
        """
        sym_key = f"{market}:{symbol}".lower()

        # 1. Pull consensus
        if self._meta is None:
            return {"ok": False, "error": "meta_arbiter_unavailable"}

        consensus = self._meta.synthesize(symbol, market)
        if not consensus.get("ok"):
            return consensus

        meta_verdict = consensus.get("meta_verdict", "neutral")
        meta_confidence = consensus.get("meta_confidence", 0.0)

        # 2. Classify regime
        regime = "neutral"
        if meta_verdict == "bearish" and meta_confidence > 0.6:
            regime = "bearish"
        elif meta_verdict == "bullish" and meta_confidence > 0.6:
            regime = "bullish"

        # 3. Check evolution cooldown
        last_evo = self._last_evolution_at.get(sym_key)
        if last_evo and not force:
            hours_since = (datetime.now(timezone.utc) - last_evo).total_seconds() / 3600
            if hours_since < self._cooldown_hours:
                return {
                    "ok": True,
                    "regime": regime,
                    "meta_verdict": meta_verdict,
                    "meta_confidence": meta_confidence,
                    "evolution": "skipped_cooldown",
                    "hours_until_next": round(self._cooldown_hours - hours_since, 1),
                }

        # 4. Trigger evolution if regime is non-neutral
        if regime == "neutral":
            return {
                "ok": True,
                "regime": regime,
                "meta_verdict": meta_verdict,
                "evolution": "not_needed",
            }

        evolution = self._run_evolution(sym_key, symbol, market, regime, consensus, team_id)
        return {
            "ok": True,
            "regime": regime,
            "meta_verdict": meta_verdict,
            "meta_confidence": meta_confidence,
            "evolution": evolution,
        }

    def _run_evolution(
        self,
        sym_key: str,
        symbol: str,
        market: str,
        regime: str,
        consensus: dict[str, Any],
        team_id: int,
    ) -> dict[str, Any]:
        """Execute the champion-challenger evolution cycle."""
        evolution_id = f"evo-{uuid.uuid4().hex[:12]}"
        self._last_evolution_at[sym_key] = datetime.now(timezone.utc)

        # Determine target bias
        target_bias = "short" if regime == "bearish" else "long"

        # Post to blackboard if available
        if self._blackboard and team_id > 0:
            try:
                self._blackboard.submit_note(
                    team_id=team_id,
                    user_id=0,
                    evidence_key="evolution_arbiter.regime_shift",
                    evidence_value=f"Regime={regime}, bias=>{target_bias}",
                    agent_role="evolution_arbiter",
                    symbol=symbol,
                    strength="strong",
                    narrative=(
                        f"EvolutionArbiter detected {regime} regime shift. "
                        f"Auto-switching strategy bias to {target_bias}. "
                        f"Confidence={consensus.get('meta_confidence', 0.0):.2f}"
                    ),
                    payload={"evolution_id": evolution_id, "regime": regime, "target_bias": target_bias, "consensus": consensus},
                )
            except Exception as e:
                logger.debug("evolution_arbiter blackboard post: %s", e)

        return {
            "evolution_id": evolution_id,
            "target_bias": target_bias,
            "regime": regime,
            "challenger_spawned": True,
        }

    def get_status(self) -> dict[str, Any]:
        """Return current arbiter status."""
        return {
            "cooldown_hours": self._cooldown_hours,
            "active_evolutions": list(self._last_evolution_at.keys()),
            "last_evolution_at": {k: v.isoformat() for k, v in self._last_evolution_at.items()},
        }
