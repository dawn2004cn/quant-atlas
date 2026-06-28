"""Evolution Arbiter service — autonomous strategy evolution via champion/challenger mesh."""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.evolution_arbiter import (
    ChallengerResult,
    ChampionStrategy,
    EvolutionState,
    Regime,
    RegimeSnapshot,
    StrategyBias,
)

logger = get_logger(__name__)


class EvolutionArbiterService:
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
            text = str(verdict).lower()
            confidence = 0.55
            regime = Regime.UNKNOWN
            if "bull" in text:
                regime = Regime.BULL_STRONG if "strong" in text else Regime.BULL_WEAK
            elif "bear" in text:
                regime = Regime.BEAR_STRONG if "strong" in text else Regime.BEAR_WEAK
            elif "range" in text:
                regime = Regime.RANGING
            elif "volatil" in text:
                regime = Regime.VOLATILE
            return RegimeSnapshot(regime=regime, confidence=confidence, source="meta_arbiter")
        except Exception as exc:
            logger.debug("regime detection failed: %s", exc)
            return RegimeSnapshot(regime=Regime.UNKNOWN, confidence=0.0, source="error")

    def get_status(self) -> dict[str, Any]:
        champion = self._state.champion
        return {
            "current_regime": self._state.current_regime.value if self._state.current_regime else Regime.UNKNOWN.value,
            "champion": dataclasses.asdict(champion) if champion else None,
            "challenger_count": len(self._state.challengers),
            "evolution_count": self._state.evolution_count,
            "last_evolution_at": self._state.last_evolution_at.isoformat() if self._state.last_evolution_at else None,
        }

    def evolve(self, symbol: str = "000001", market: str = "CN", challenger_count: int = 2) -> dict[str, Any]:
        snapshot = self.detect_regime(symbol, market)
        self._state.current_regime = snapshot.regime
        challengers = self._spawn_challengers(symbol, market, challenger_count)
        self._state.challengers = challengers
        best = max(challengers, key=_challenger_score, default=None)
        if best is None:
            return {"ok": True, "action": "no_challengers", "regime": snapshot.regime.value}
        champion = self._state.champion
        promoted = False
        if champion is None or _challenger_score(best) > _challenger_score(champion):
            self._state.champion = ChampionStrategy(
                strategy_id=best.strategy_id,
                name=best.name,
                bias=best.bias,
                performance_score=_challenger_score(best),
                deployed_at=datetime.now(),
            )
            self._state.last_evolution_at = datetime.now()
            self._state.evolution_count += 1
            promoted = True
        return {
            "ok": True,
            "action": "promoted" if promoted else "retain",
            "regime": snapshot.regime.value,
            "best_challenger": dataclasses.asdict(best),
            "champion": dataclasses.asdict(self._state.champion) if self._state.champion else None,
        }

    def _spawn_challengers(self, symbol: str, market: str, count: int) -> list[ChallengerResult]:
        out: list[ChallengerResult] = []
        for i in range(max(1, count)):
            sid = f"challenger-{datetime.now().strftime('%H%M%S')}-{i}"
            bias = {
                Regime.BULL_STRONG: StrategyBias.LONG,
                Regime.BULL_WEAK: StrategyBias.LONG,
                Regime.BEAR_STRONG: StrategyBias.SHORT,
                Regime.BEAR_WEAK: StrategyBias.SHORT,
                Regime.RANGING: StrategyBias.NEUTRAL,
                Regime.VOLATILE: StrategyBias.HEDGE,
            }.get(self._state.current_regime or Regime.UNKNOWN, StrategyBias.NEUTRAL)
            base = ChallengerResult(strategy_id=sid, name=f"Evo-{sid[-4:]}", bias=bias)
            simulated = self._simulate_challenger(symbol, market, base)
            out.append(simulated)
        return out

    def _simulate_challenger(self, symbol: str, market: str, base: ChallengerResult) -> ChallengerResult:
        if self._sim is None:
            return base
        try:
            from app.domain.simulation_scenario import (
                SimulationScenario,
                SimulationScenarioType,
                WarRoomRunRequest,
            )
            scenario = SimulationScenario(
                scenario_type=SimulationScenarioType.CUSTOM_HYPOTHESIS,
                scenario_id=f"evo-{base.strategy_id}",
                label=base.name,
                description=f"Evolution challenger {base.name} bias={base.bias.value}",
                config={"bias": base.bias.value, "symbol": symbol, "market": market},
            )
            request = WarRoomRunRequest(
                scenario=scenario,
                positions=[],
                cash=100000.0,
                use_watchlist_fallback=False,
                run_arbiter=False,
                inject_virtual_events=False,
            )
            result = self._sim.run_war_room(user_id=0, request=request)
            pnl = 0.0
            sharpe = 0.0
            max_dd = 0.0
            if isinstance(result, dict):
                pnl = float(result.get("portfolio_pnl") or result.get("pnl") or 0.0)
                sharpe = float(result.get("sharpe_ratio") or result.get("sharpe") or 0.0)
                max_dd = float(result.get("max_drawdown") or 0.0)
            return ChallengerResult(
                strategy_id=base.strategy_id,
                name=base.name,
                bias=base.bias,
                shadow_pnl=pnl,
                sharpe=sharpe,
                max_drawdown=max_dd,
            )
        except Exception as exc:
            logger.debug("simulation failed for %s: %s", base.strategy_id, exc)
            return base


def _challenger_score(c: ChallengerResult | None) -> float:
    if c is None:
        return 0.0
    return float(c.shadow_pnl or 0.0) + 0.3 * float(c.sharpe or 0.0)
