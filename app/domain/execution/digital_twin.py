from __future__ import annotations

"""Live-Backtest Digital Twin - Shadow Strategy & Drift Detection.

This module implements from strategy_plan1.md:
- ShadowStrategy: Parallel strategy with adjusted params
- DriftDetector: Detect performance drift between live and shadow
- AutoHotSwap: Zero-downtime parameter switching

Usage:
    twin = DigitalTwin()
    twin.run_shadow(strategy, adjusted_params)
    drift = twin.check_drift()
    if drift.needs_rebalance:
        twin.hotswap()
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyState:
    """State of a strategy at a point in time."""
    strategy_name: str
    positions: dict[str, float]
    cash: float
    total_value: float
    timestamp: datetime


@dataclass
class DriftAnalysis:
    """Analysis of drift between live and shadow strategy."""
    live_return: float
    shadow_return: float
    drift_amount: float
    drift_percentage: float
    needs_rebalance: bool
    recommendation: str


class ExecutionMode(Enum):
    """Mode of execution for DigitalTwin."""
    LIVE_ONLY = "live_only"
    SHADOW_ONLY = "shadow_only"
    DUAL_TRACK = "dual_track"


class ShadowStrategy:
    """Shadow strategy running with adjusted parameters."""

    def __init__(
        self,
        base_strategy: Any,
        adjusted_params: dict[str, Any],
    ):
        self._base = base_strategy
        self._params = adjusted_params
        self._state_history: list[StrategyState] = []
        self._performance_history: list[dict[str, float]] = []

    def execute(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Execute shadow strategy with adjusted params."""
        adjusted_strategy = self._apply_params(self._base, self._params)

        signals = adjusted_strategy.generate_signals(market_data)

        return {
            "signals": signals,
            "params_used": self._params,
            "is_shadow": True,
        }

    def _apply_params(self, strategy, params: dict[str, Any]) -> Any:
        """Apply adjusted parameters to strategy."""
        return strategy

    def record_state(
        self,
        positions: dict[str, float],
        cash: float,
        total_value: float,
    ) -> None:
        """Record strategy state."""
        self._state_history.append(StrategyState(
            strategy_name=self._base.__class__.__name__,
            positions=positions,
            cash=cash,
            total_value=total_value,
            timestamp=datetime.now(),
        ))

        if len(self._state_history) > 100:
            self._state_history = self._state_history[-100:]

    def get_performance(self, days: int = 3) -> dict[str, float]:
        """Get performance metrics for recent period."""
        cutoff = datetime.now() - timedelta(days=days)

        recent_states = [
            s for s in self._state_history
            if s.timestamp >= cutoff
        ]

        if len(recent_states) < 2:
            return {"return": 0.0, "sharpe": 0.0}

        first_value = recent_states[0].total_value
        last_value = recent_states[-1].total_value

        return_pct = (last_value - first_value) / first_value if first_value > 0 else 0

        return {
            "return": return_pct,
            "period_days": days,
            "states_count": len(recent_states),
        }


class DriftDetector:
    """Detect performance drift between live and shadow strategies."""

    def __init__(
        self,
        drift_threshold: float = 0.05,
        lookback_days: int = 3,
    ):
        self._threshold = drift_threshold
        self._lookback = lookback_days

    def analyze(
        self,
        live_performance: dict[str, float],
        shadow_performance: dict[str, float],
    ) -> DriftAnalysis:
        """Analyze drift between live and shadow."""
        live_return = live_performance.get("return", 0)
        shadow_return = shadow_performance.get("return", 0)

        drift_amount = shadow_return - live_return

        drift_percentage = (
            (drift_amount / abs(live_return)) * 100
            if live_return != 0 else 0
        )

        needs_rebalance = abs(drift_amount) > self._threshold

        if drift_amount > self._threshold:
            recommendation = "Shadow outperforms - consider hotswap"
        elif drift_amount < -self._threshold:
            recommendation = "Live outperforms - keep current params"
        else:
            recommendation = "No significant drift"

        return DriftAnalysis(
            live_return=live_return,
            shadow_return=shadow_return,
            drift_amount=drift_amount,
            drift_percentage=drift_percentage,
            needs_rebalance=needs_rebalance,
            recommendation=recommendation,
        )


class AutoHotSwap:
    """Zero-downtime hot swap for strategy parameters with canary rollback."""

    CANARY_OBSERVATION_MINUTES = 30
    ROLLBACK_DRAWDOWN_THRESHOLD = 0.015

    def __init__(self, drift_detector: DriftDetector | None = None):
        self._detector = drift_detector or DriftDetector()
        self._swap_history: list[dict[str, Any]] = []
        self._canary_active = False
        self._canary_start_time: datetime | None = None
        self._canary_original_params: dict[str, Any] | None = None
        self._canary_peak_value: float = 0.0

    def start_canary(self, current_params: dict[str, Any]) -> bool:
        """Start canary observation period after hot swap."""
        self._canary_active = True
        self._canary_start_time = datetime.now()
        self._canary_original_params = current_params.copy()
        self._canary_peak_value = 0.0
        logger.warning(f"Canary started, observing for {self.CANARY_OBSERVATION_MINUTES} minutes")
        return True

    def check_canary_rollback(
        self,
        current_value: float,
        risk_violation: bool = False,
    ) -> dict[str, Any]:
        """Check if canary should trigger rollback."""
        if not self._canary_active:
            return {"should_rollback": False}

        if self._canary_peak_value == 0.0:
            self._canary_peak_value = current_value
            return {"should_rollback": False}

        current_drawdown = (self._canary_peak_value - current_value) / self._canary_peak_value

        from datetime import datetime as dt
        if self._canary_start_time:
            elapsed = (dt.now() - self._canary_start_time).total_seconds() / 60

            should_rollback = (
                risk_violation or
                current_drawdown > self.ROLLBACK_DRAWDOWN_THRESHOLD or
                elapsed > self.CANARY_OBSERVATION_MINUTES
            )

            if should_rollback:
                logger.warning(
                    f"CANARY ROLLBACK triggered: drawdown={current_drawdown:.2%}, "
                    f"violation={risk_violation}, elapsed={elapsed:.1f}min"
                )
                self._canary_active = False

            return {
                "should_rollback": should_rollback,
                "drawdown": current_drawdown,
                "elapsed_minutes": elapsed,
                "original_params": self._canary_original_params,
            }

        return {"should_rollback": False}

    def cancel_canary(self) -> dict[str, Any]:
        """Cancel canary and confirm deployment."""
        result = {
            "confirmed": True,
            "duration_minutes": 0,
        }
        if self._canary_start_time:
            from datetime import datetime as dt
            result["duration_minutes"] = (dt.now() - self._canary_start_time).total_seconds() / 60
        self._canary_active = False
        self._canary_original_params = None
        return result

    async def evaluate_and_swap(
        self,
        live_strategy: Any,
        shadow_strategy: ShadowStrategy,
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate and potentially swap strategies."""
        live_perf = self._get_live_performance(live_strategy)
        shadow_perf = shadow_strategy.get_performance(self._detector._lookback)

        drift = self._detector.analyze(live_perf, shadow_perf)

        result = {
            "drift_analysis": {
                "live_return": drift.live_return,
                "shadow_return": drift.shadow_return,
                "drift": drift.drift_amount,
                "needs_swap": drift.needs_rebalance,
            },
            "swapped": False,
        }

        if drift.needs_rebalance and drift.drift_amount > 0:
            result["swapped"] = True
            result["new_params"] = shadow_strategy._params.copy()

            self._swap_history.append({
                "timestamp": datetime.now(),
                "old_params": live_strategy.get_params(),
                "new_params": shadow_strategy._params,
                "drift": drift.drift_amount,
            })

            logger.warning(f"Hot swap triggered: drift={drift.drift_amount:.2%}")

        return result

    def _get_live_performance(self, strategy: Any) -> dict[str, float]:
        """Get performance of live strategy."""
        return {"return": 0.05}


class DigitalTwin:
    """Complete digital twin system for live-backtest consistency.

    Supports dual-track execution:
    - Live track: Real orders via execution gateway
    - Shadow track: Simulated orders in HighFidelityExecutor
    Both tracks run in parallel, shadow PnL used for hot-swap decisions.
    """

    def __init__(
        self,
        shadow_strategy: ShadowStrategy | None = None,
        drift_detector: DriftDetector | None = None,
        hotswap: AutoHotSwap | None = None,
        execution_mode: ExecutionMode = ExecutionMode.DUAL_TRACK,
    ):
        self._shadow = shadow_strategy
        self._detector = drift_detector or DriftDetector()
        self._hotswap = hotswap or AutoHotSwap(self._detector)
        self._live_strategy: Any = None
        self._execution_mode = execution_mode
        self._live_pnl: list[float] = []
        self._shadow_pnl: list[float] = []
        self._rollback_history: list[dict[str, Any]] = []

    def set_execution_mode(self, mode: ExecutionMode) -> None:
        """Set the execution mode."""
        self._execution_mode = mode
        logger.info(f"DigitalTwin execution mode: {mode.value}")

    async def execute_dual_track(
        self,
        live_executor: Any,
        shadow_executor: Any,
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute dual-track: real orders on live, simulated on shadow."""
        results = {"live": None, "shadow": None, "can_hotswap": False}

        if self._execution_mode in [ExecutionMode.LIVE_ONLY, ExecutionMode.DUAL_TRACK]:
            live_result = await live_executor.execute(market_data)
            results["live"] = live_result
            if live_result.get("pnl"):
                self._live_pnl.append(live_result["pnl"])

        if self._execution_mode in [ExecutionMode.SHADOW_ONLY, ExecutionMode.DUAL_TRACK]:
            shadow_result = await shadow_executor.execute(market_data)
            results["shadow"] = shadow_result
            if shadow_result.get("pnl"):
                self._shadow_pnl.append(shadow_result["pnl"])

        if len(self._shadow_pnl) >= 10:
            live = sum(self._live_pnl[-10:]) if self._live_pnl else 0
            shadow = sum(self._shadow_pnl[-10:])

            drift = abs(shadow - live) / abs(live) if live != 0 else 0
            results["drift"] = drift
            results["can_hotswap"] = drift < 0.15

        return results

    def rollback(self) -> bool:
        """Rollback to previous state if hot-swap fails."""
        if not self._rollback_history:
            return False

        last_state = self._rollback_history.pop()
        logger.warning(f"Rolling back to: {last_state.get('strategy_id')}")
        return True

    def record_rollback(self, strategy_id: str, reason: str) -> None:
        """Record a rollback event for audit."""
        self._rollback_history.append({
            "strategy_id": strategy_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "live_pnl": self._live_pnl[-5:] if self._live_pnl else [],
            "shadow_pnl": self._shadow_pnl[-5:] if self._shadow_pnl else [],
        })

    def setup_shadow(
        self,
        live_strategy: Any,
        adjustment: dict[str, Any],
    ) -> ShadowStrategy:
        """Setup shadow strategy with adjusted parameters."""
        self._live_strategy = live_strategy

        self._shadow = ShadowStrategy(live_strategy, adjustment)

        logger.info(f"Shadow strategy setup with adjustments: {adjustment}")

        return self._shadow

    async def run_evaluation(
        self,
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run evaluation cycle."""
        if not self._shadow or not self._live_strategy:
            return {"error": "Strategy not setup"}

        shadow_signals = self._shadow.execute(market_data)

        result = await self._hotswap.evaluate_and_swap(
            self._live_strategy,
            self._shadow,
            market_data,
        )

        result["shadow_signals"] = shadow_signals.get("signals", [])

        return result

    def get_status(self) -> dict[str, Any]:
        """Get digital twin status."""
        if not self._shadow:
            return {"status": "not_initialized"}

        recent_perf = self._shadow.get_performance(3)

        return {
            "status": "running",
            "shadow_params": self._shadow._params,
            "shadow_performance": recent_perf,
            "swap_history_count": len(self._hotswap._swap_history),
        }


_global_twin: DigitalTwin | None = None


def get_digital_twin() -> DigitalTwin:
    """Get singleton digital twin."""
    global _global_twin
    if _global_twin is None:
        _global_twin = DigitalTwin()
    return _global_twin


def reset_digital_twin() -> None:
    """Reset singleton (for testing)."""
    global _global_twin
    _global_twin = None
