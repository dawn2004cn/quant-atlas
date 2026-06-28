from __future__ import annotations
"""TCA Auto-Calibration - Transaction Cost Analysis Feedback.

Implements from strategy_plan3.md:
- Real-time slippage tracking from live executions
- Auto-calibrate backtest engine parameters
- Feedback loop to eliminate 'lab hallucination'

Usage:
    tca = TCAAutoCalibrator()
    tca.record_execution(slippage=0.001, market_impact=0.0005)
    adjustment = tca.get_calibration_factor()
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import deque

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionRecord:
    """Single execution record for TCA."""
    symbol: str
    timestamp: datetime
    side: str
    quantity: int
    fill_price: float
    mid_price: float
    spread_cost: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0


@dataclass
class CalibrationFactors:
    """Calibration factors for backtest engine."""
    slippage_multiplier: float = 1.0
    market_impact_multiplier: float = 1.0
    spread_multiplier: float = 1.0
    liquidity_discount: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)
    sample_size: int = 0


class TCAAutoCalibrator:
    """TCA auto-calibration for backtest alignment."""

    DEFAULT_HALF_LIFE_HOURS = 24
    MIN_SAMPLES = 30

    def __init__(self, half_life_hours: int = DEFAULT_HALF_LIFE_HOURS):
        self._records: deque[ExecutionRecord] = deque(maxlen=1000)
        self._factors = CalibrationFactors()
        self._half_life_hours = half_life_hours
        self._drift_count = 0

    def record_execution(
        self,
        symbol: str,
        timestamp: datetime,
        side: str,
        quantity: int,
        fill_price: float,
        mid_price: float,
    ) -> None:
        """Record execution for TCA analysis."""
        spread = abs(fill_price - mid_price) / mid_price if mid_price > 0 else 0
        slippage = spread * 0.5

        impact = spread * 0.3 if side.upper() in ["BUY", "SELL"] else 0

        record = ExecutionRecord(
            symbol=symbol,
            timestamp=timestamp,
            side=side,
            quantity=quantity,
            fill_price=fill_price,
            mid_price=mid_price,
            spread_cost=spread,
            slippage=slippage,
            market_impact=impact,
        )

        self._records.append(record)
        logger.debug(f"Recorded TCA: {symbol} slippage={slippage:.4%}")

    def update_calibration(self) -> CalibrationFactors:
        """Update calibration factors based on recent executions."""
        cutoff = datetime.now() - timedelta(hours=self._half_life_hours)
        recent = [r for r in self._records if r.timestamp > cutoff]

        if len(recent) < self.MIN_SAMPLES:
            logger.warning(f"Insufficient TCA samples: {len(recent)}")
            return self._factors

        slippage_samples = [r.slippage for r in recent if r.slippage > 0]
        impact_samples = [r.market_impact for r in recent if r.market_impact > 0]

        if slippage_samples:
            avg_slippage = sum(slippage_samples) / len(slippage_samples)
            self._factors.slippage_multiplier = max(1.0, avg_slippage * 100)
        else:
            avg_slippage = 0.0

        if impact_samples:
            avg_impact = sum(impact_samples) / len(impact_samples)
            self._factors.market_impact_multiplier = max(1.0, avg_impact * 100)
        else:
            avg_impact = 0.0

        self._factors.spread_multiplier = self._factors.slippage_multiplier

        large_trades = [r for r in recent if r.quantity > 10000]
        if large_trades:
            large_impact = sum(r.market_impact for r in large_trades) / len(large_trades)
            self._factors.liquidity_discount = large_impact * 0.5
        else:
            self._factors.liquidity_discount = 0.0

        self._factors.sample_size = len(recent)
        self._factors.updated_at = datetime.now()

        logger.info(
            f"TCA calibrated: slippage={self._factors.slippage_multiplier:.2f}, "
            f"impact={self._factors.market_impact_multiplier:.2f}, samples={len(recent)}"
        )

        return self._factors

    def get_calibration_factor(self) -> float:
        """Get combined calibration factor for backtest engine."""
        return (
            self._factors.slippage_multiplier * 0.4 +
            self._factors.market_impact_multiplier * 0.4 +
            self._factors.spread_multiplier * 0.2
        )

    def detect_drift(self) -> bool:
        """Detect calibration drift."""
        if len(self._records) < self.MIN_SAMPLES:
            return False

        old_cutoff = datetime.now() - timedelta(hours=self._half_life_hours * 2)
        old = [r for r in self._records if r.timestamp <= old_cutoff]

        new_cutoff = datetime.now() - timedelta(hours=self._half_life_hours)
        new = [r for r in self._records if r.timestamp > new_cutoff]

        if len(new) < 10:
            return False

        old_slip = sum(r.slippage for r in old) / len(old) if old else 0
        new_slip = sum(r.slippage for r in new) / len(new)

        drift = abs(new_slip - old_slip) / (old_slip + 1e-10)

        if drift > 0.3:
            self._drift_count += 1
            logger.warning(f"TCA drift detected: {drift:.2%}")
            return True

        return False

    def get_tca_summary(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get TCA summary."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [r for r in self._records if r.timestamp > cutoff]

        if not recent:
            return {"sample_size": 0}

        return {
            "sample_size": len(recent),
            "avg_slippage": sum(r.slippage for r in recent) / len(recent),
            "avg_impact": sum(r.market_impact for r in recent) / len(recent),
            "max_slippage": max(r.slippage for r in recent),
            "calibration_factor": self.get_calibration_factor(),
            "factors": {
                "slippage": self._factors.slippage_multiplier,
                "impact": self._factors.market_impact_multiplier,
                "spread": self._factors.spread_multiplier,
            },
        }


class BacktestCalibrator:
    """Calibrate backtest engine with TCA feedback."""

    def __init__(self, tca: TCAAutoCalibrator = None):
        self._tca = tca or TCAAutoCalibrator()
        self._calibration_history: list[tuple[CalibrationFactors, datetime]] = []

    def calibrate_backtest_params(
        self,
    ) -> dict[str, float]:
        """Get calibrated backtest parameters."""
        factors = self._tca.update_calibration()
        self._calibration_history.append((factors, datetime.now()))

        return {
            "slippage_bps": factors.slippage_multiplier * 10,
            "market_impact_bps": factors.market_impact_multiplier * 10,
            "spread_bps": factors.spread_multiplier * 10,
            "liquidity_discount": factors.liquidity_discount,
        }

    def get_recommended_fees(
        self,
        symbol: str,
    ) -> dict[str, float]:
        """Get recommended fee structure for symbol."""
        factor = self._tca.get_calibration_factor()

        base_commission = 0.0003
        calibrated = base_commission * factor

        return {
            "commission": calibrated,
            "slippage": calibrated * 0.5,
            "market_impact": calibrated * 0.3,
            "total": calibrated * 1.2,
        }


_global_tca: TCAAutoCalibrator | None = None


def get_tca_calibrator() -> TCAAutoCalibrator:
    """Get global TCA calibrator."""
    global _global_tca
    if _global_tca is None:
        _global_tca = TCAAutoCalibrator()
    return _global_tca
