from __future__ import annotations

"""Factor Lifecycle Management - Alpha Factor Tracking & Auto-Decay.

This module implements from strategy_plan.md:
- FactorDashboard: Real-time IC, IR, turnover tracking
- AutoDecay: Trigger retraining or removal when IR drops
- FactorNeutralization: Industry/style neutralization

Usage:
    factor_mgr = FactorLifecycleManager()
    factor_mgr.track_factor("ma_crossover", ic=0.05, ir=1.2)
    decay_alert = factor_mgr.check_decay("ma_crossover")
"""


from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FactorMetrics:
    """Metrics for a single factor."""
    factor_name: str
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ir: float = 0.0
    turnover: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    historical_ics: list[float] = field(default_factory=list)


@dataclass
class FactorDecayAlert:
    """Alert for factor decay."""
    factor_name: str
    severity: str
    current_ir: float
    threshold_ir: float
    recommended_action: str
    triggered_at: datetime


class FactorDashboard:
    """Dashboard for tracking factor metrics in real-time."""

    def __init__(self):
        self._factors: dict[str, FactorMetrics] = {}

    def record_metrics(
        self,
        factor_name: str,
        ic: float,
        turnover: float = 0.0,
    ) -> None:
        """Record factor metrics for a period."""
        if factor_name not in self._factors:
            self._factors[factor_name] = FactorMetrics(factor_name=factor_name)

        metrics = self._factors[factor_name]

        metrics.historical_ics.append(ic)
        if len(metrics.historical_ics) > 60:
            metrics.historical_ics = metrics.historical_ics[-60:]

        recent_ics = metrics.historical_ics[-14:]
        metrics.ic_mean = sum(recent_ics) / len(recent_ics) if recent_ics else 0.0
        metrics.ic_std = (sum((x - metrics.ic_mean) ** 2 for x in recent_ics) / len(recent_ics)) ** 0.5 if recent_ics else 1.0
        metrics.ir = metrics.ic_mean / metrics.ic_std if metrics.ic_std > 0 else 0.0
        metrics.turnover = turnover
        metrics.last_updated = datetime.now()

    def get_factor_status(self, factor_name: str) -> FactorMetrics | None:
        """Get current status of a factor."""
        return self._factors.get(factor_name)

    def get_all_factors(self) -> list[FactorMetrics]:
        """Get all factors sorted by IR."""
        return sorted(
            self._factors.values(),
            key=lambda x: x.ir,
            reverse=True,
        )

    def get_top_performers(self, limit: int = 10) -> list[FactorMetrics]:
        """Get top performing factors by IR."""
        return self.get_all_factors()[:limit]


class FactorDecayDetector:
    """Detect factor decay and trigger alerts."""

    def __init__(
        self,
        ir_threshold: float = 0.5,
        decay_window_days: int = 14,
    ):
        self._ir_threshold = ir_threshold
        self._decay_window = decay_window_days

    def check_decay(
        self,
        factor: FactorMetrics,
    ) -> FactorDecayAlert | None:
        """Check if factor is decaying."""
        if factor.ir < self._ir_threshold:
            if factor.ir < self._ir_threshold * 0.5:
                severity = "critical"
                action = "remove"
            else:
                severity = "warning"
                action = "retrain"

            return FactorDecayAlert(
                factor_name=factor.factor_name,
                severity=severity,
                current_ir=factor.ir,
                threshold_ir=self._ir_threshold,
                recommended_action=action,
                triggered_at=datetime.now(),
            )

        return None


class FactorNeutralizer:
    """Neutralize factor exposures to industry and style."""

    def __init__(self):
        self._style_factors = ["size", "value", "momentum", "volatility", "quality"]

    def neutralize(
        self,
        factor_values: dict[str, float],
        exposures: dict[str, float],
    ) -> dict[str, float]:
        """Apply neutralization to factor values."""
        neutralized = {}

        for factor_name, value in factor_values.items():
            if factor_name in self._style_factors:
                neutralized[factor_name] = value - exposures.get(factor_name, 0.0)
            else:
                neutralized[factor_name] = value

        return neutralized


class FactorLifecycleManager:
    """Complete factor lifecycle management."""

    def __init__(
        self,
        ir_threshold: float = 0.5,
    ):
        self._dashboard = FactorDashboard()
        self._decay_detector = FactorDecayDetector(ir_threshold=ir_threshold)
        self._neutralizer = FactorNeutralizer()

    def track_factor(
        self,
        factor_name: str,
        ic: float,
        turnover: float = 0.0,
    ) -> None:
        """Track factor metrics."""
        self._dashboard.record_metrics(factor_name, ic, turnover)

    def check_decay(self, factor_name: str) -> FactorDecayAlert | None:
        """Check factor for decay."""
        factor = self._dashboard.get_factor_status(factor_name)
        if factor:
            return self._decay_detector.check_decay(factor)
        return None

    def get_decay_alerts(self) -> list[FactorDecayAlert]:
        """Get all decay alerts across factors."""
        alerts = []
        for factor in self._dashboard.get_all_factors():
            alert = self._decay_detector.check_decay(factor)
            if alert:
                alerts.append(alert)
        return alerts

    def neutralize_factor(
        self,
        factor_values: dict[str, float],
        exposures: dict[str, float],
    ) -> dict[str, float]:
        """Neutralize factor exposures."""
        return self._neutralizer.neutralize(factor_values, exposures)

    def get_dashboard(self) -> FactorDashboard:
        """Get factor dashboard."""
        return self._dashboard


_global_factor_manager: FactorLifecycleManager | None = None


def get_factor_manager() -> FactorLifecycleManager:
    """Get singleton factor manager."""
    global _global_factor_manager
    if _global_factor_manager is None:
        _global_factor_manager = FactorLifecycleManager()
    return _global_factor_manager
