from __future__ import annotations

"""Factor Service - manages factor lifecycle and performance tracking.

This module provides:
- Factor CRUD operations
- IC/IR calculation
- Decay detection and alerting
- Factor ranking and selection
"""


import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from app.domain.ports.factor_repository_port import FactorRepositoryPort as _FactorRepo

logger = logging.getLogger(__name__)


class FactorService:
    """Service for managing factor lifecycle and performance."""

    def __init__(self, factor_repository: _FactorRepo):
        self._repo = factor_repository

    async def register_factor(
        self,
        factor_name: str,
        factor_expression: str,
        category: str = "custom",
        description: str = "",
    ) -> str:
        """Register a new factor.

        Args:
            factor_name: Human-readable name
            factor_expression: Factor expression/formula
            category: Factor category (momentum, value, quality, etc.)
            description: Optional description

        Returns:
            Factor ID
        """
        factor_id = f"factor_{uuid.uuid4().hex[:12]}"

        factor_data = {
            "factor_id": factor_id,
            "factor_name": factor_name,
            "factor_expression": factor_expression,
            "category": category,
            "description": description,
            "effective_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
            "owner": "system",
        }

        await self._repo.create_factor(factor_data)
        logger.info(f"Registered new factor: {factor_name} ({factor_id})")

        return factor_id

    async def update_factor_performance(
        self,
        factor_id: str,
        ic_series: list[float],
    ) -> dict[str, float]:
        """Update factor performance metrics from IC series.

        Args:
            factor_id: Factor ID
            ic_series: List of IC values over time

        Returns:
            Updated metrics (ic_mean, ic_std, ir, decay_rate)
        """
        if len(ic_series) < 10:
            logger.warning(f"Insufficient IC data for factor {factor_id}")
            return {}

        ic_mean = float(np.mean(ic_series))
        ic_std = float(np.std(ic_series))
        ir = ic_mean / ic_std if ic_std > 0 else 0.0

        decay_rate = self._calculate_decay_rate(ic_series)

        await self._repo.update_factor_performance(
            factor_id=factor_id,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ir=ir,
            decay_rate=decay_rate,
        )

        await self._record_ic_history(factor_id, ic_series)

        logger.info(
            f"Updated factor {factor_id}: IC={ic_mean:.4f}, IR={ir:.4f}, Decay={decay_rate:.4f}"
        )

        return {
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "ir": ir,
            "decay_rate": decay_rate,
        }

    def _calculate_decay_rate(self, ic_series: list[float], window: int = 20) -> float:
        """Calculate factor decay rate.

        Measures how quickly factor IC degrades over time.
        Uses rolling window correlation between IC and time.

        Args:
            ic_series: IC values over time
            window: Rolling window size

        Returns:
            Decay rate (higher = faster decay)
        """
        if len(ic_series) < window:
            return 0.0

        recent_ic = ic_series[-window:]
        x = np.arange(len(recent_ic))
        y = np.array(recent_ic)

        if np.std(y) == 0:
            return 0.0

        correlation = np.corrcoef(x, y)[0, 1]
        return max(0.0, -correlation)

    async def _record_ic_history(self, factor_id: str, ic_series: list[float]) -> None:
        """Record IC history for a factor."""
        datetime.now().strftime("%Y-%m-%d")

        for i, ic_value in enumerate(ic_series[-60:]):
            calc_date = (datetime.now() - timedelta(days=59 - i)).strftime("%Y-%m-%d")
            await self._repo.add_ic_record(
                factor_id=factor_id,
                calc_date=calc_date,
                ic_value=ic_value,
                sample_count=100,
            )

    async def detect_decay(
        self,
        factor_id: str,
        lookback_days: int = 60,
        decay_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Detect factor decay and trigger alerts.

        Args:
            factor_id: Factor ID to check
            lookback_days: Days to analyze
            decay_threshold: Threshold for decay detection

        Returns:
            Decay detection result
        """
        factor = await self._repo.get_factor(factor_id)
        if not factor:
            return {"detected": False, "reason": "factor_not_found"}

        ic_history = await self._repo.get_ic_history(factor_id, days=lookback_days)
        if len(ic_history) < 20:
            return {"detected": False, "reason": "insufficient_data"}

        recent_ic = [r["ic_value"] for r in ic_history[-20:]]
        historical_ic = [r["ic_value"] for r in ic_history[:20]]

        recent_mean = np.mean(recent_ic)
        historical_mean = np.mean(historical_ic)

        if historical_mean == 0:
            return {"detected": False, "reason": "zero_historical_ic"}

        decay_ratio = (historical_mean - recent_mean) / abs(historical_mean)

        detected = decay_ratio > decay_threshold and abs(recent_mean) < abs(historical_mean)

        severity = "critical" if decay_ratio > 0.5 else "warning" if decay_ratio > 0.3 else "normal"

        if detected:
            await self._repo.log_decay_event(
                factor_id=factor_id,
                detection_date=datetime.now().strftime("%Y-%m-%d"),
                ic_mean_current=recent_mean,
                ic_mean_historical=historical_mean,
                decay_ratio=decay_ratio,
                severity=severity,
            )

            logger.warning(
                f"Factor decay detected: {factor_id}, decay_ratio={decay_ratio:.2%}, severity={severity}"
            )

        return {
            "detected": detected,
            "decay_ratio": decay_ratio,
            "severity": severity,
            "recent_ic_mean": recent_mean,
            "historical_ic_mean": historical_mean,
        }

    async def auto_degrade_factors(self, min_ir: float = 0.3) -> int:
        """Automatically degrade underperforming factors.

        Args:
            min_ir: Minimum IR threshold

        Returns:
            Number of factors degraded
        """
        top_factors = await self._repo.get_top_factors(limit=1000, min_ir=0.0)
        degraded_count = 0

        for factor in top_factors:
            if factor["ir"] < min_ir and factor["status"] == "active":
                await self._repo.deactivate_factor(
                    factor["factor_id"],
                    reason=f"IR below threshold ({factor['ir']:.4f} < {min_ir})",
                )
                logger.info(f"Degraded factor: {factor['factor_name']} (IR={factor['ir']:.4f})")
                degraded_count += 1

        return degraded_count

    async def get_factor_leaderboard(
        self,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get factor leaderboard by IR.

        Args:
            category: Optional category filter
            limit: Number of factors to return

        Returns:
            List of top factors with metrics
        """
        factors = await self._repo.list_factors(
            category=category,
            status="active",
            order_by="ir",
            limit=limit,
        )

        return [
            {
                "rank": i + 1,
                "factor_id": f["factor_id"],
                "factor_name": f["factor_name"],
                "category": f["category"],
                "ic_mean": f["ic_mean"],
                "ic_std": f["ic_std"],
                "ir": f["ir"],
                "decay_rate": f["decay_rate"],
            }
            for i, f in enumerate(factors)
        ]

    async def calculate_ic_for_factor(
        self,
        factor_id: str,
        factor_values: dict[str, float],
        forward_returns: dict[str, float],
    ) -> float:
        """Calculate IC for a single calculation.

        Args:
            factor_id: Factor ID
            factor_values: Dict of symbol -> factor value
            forward_returns: Dict of symbol -> forward return

        Returns:
            IC value
        """
        symbols = list(factor_values.keys())
        if not symbols:
            return 0.0

        factor_array = np.array([factor_values.get(s, 0) for s in symbols])
        return_array = np.array([forward_returns.get(s, 0) for s in symbols])

        if np.std(factor_array) == 0 or np.std(return_array) == 0:
            return 0.0

        ic = np.corrcoef(factor_array, return_array)[0, 1]
        return float(ic)


class FactorFactory:
    """Factory for creating common factor types."""

    @staticmethod
    def create_momentum_factor(days: int = 20) -> dict[str, str]:
        """Create a momentum factor expression."""
        return {
            "factor_name": f"momentum_{days}d",
            "factor_expression": f"rank(returns_{days}d)",
            "category": "momentum",
            "description": f"{days}-day momentum factor",
        }

    @staticmethod
    def create_value_factor() -> dict[str, str]:
        """Create a value factor expression."""
        return {
            "factor_name": "pb_ratio",
            "factor_expression": "rank(-pb)",
            "category": "value",
            "description": "Price-to-Book ratio factor",
        }

    @staticmethod
    def create_quality_factor() -> dict[str, str]:
        """Create a quality factor expression."""
        return {
            "factor_name": "roe_quality",
            "factor_expression": "rank(roe)",
            "category": "quality",
            "description": "ROE-based quality factor",
        }


__all__ = ["FactorService", "FactorFactory"]
