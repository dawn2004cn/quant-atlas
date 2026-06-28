from __future__ import annotations
"""Factor Lifecycle Manager - 因子生命周期自动化管理.

Phase 41: 因子生命周期管理

This module provides automated factor lifecycle management:
- Factor state machine: active -> monitoring -> deprecated -> archived
- Auto-deactivation when IC drops below threshold for N consecutive days
- Integration with FactorMiner for seamless factor registration
- Scheduled tasks for daily IC calculation and decay detection
"""


import logging
from enum import Enum
from typing import Any

import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.ports.factor_repository_port import FactorRepositoryPort as _FactorRepo

logger = logging.getLogger(__name__)


class FactorState(Enum):
    """Factor lifecycle states."""

    ACTIVE = "active"  # 正常使用的因子
    MONITORING = "monitoring"  # 性能下降，观察中
    DEPRECATED = "deprecated"  # 已下架，不再使用
    ARCHIVED = "archived"  # 已归档，仅保留历史


class FactorLifecycleConfig:
    """Configuration for factor lifecycle management."""

    # IC 阈值
    IC_THRESHOLD_ACTIVE: float = 0.03  # 活跃因子最低 IC
    IC_THRESHOLD_MONITORING: float = 0.02  # 观察期最低 IC
    IR_THRESHOLD: float = 0.3  # 信息比率阈值

    # 连续天数阈值
    CONSECUTIVE_DAYS_BELOW_THRESHOLD: int = 5  # 连续低于阈值的天数
    LOOKBACK_DAYS: int = 60  # 回看天数

    # 衰减阈值
    DECAY_THRESHOLD_WARNING: float = 0.3  # 衰减警告阈值
    DECAY_THRESHOLD_CRITICAL: float = 0.5  # 衰减严重阈值


class FactorLifecycleManager:
    """Manages factor lifecycle from creation to archival.

    This class implements the "survival of the fittest" mechanism:
    1. Registers new factors from FactorMiner
    2. Tracks daily IC performance
    3. Detects decay and triggers state transitions
    4. Auto-deactivates underperforming factors
    """

    def __init__(
        self,
        factor_repository: _FactorRepo,
        config: FactorLifecycleConfig | None = None,
    ):
        from app.domain.factor_service import FactorService
        self._repo = factor_repository
        self._config = config or FactorLifecycleConfig()
        self._factor_service = FactorService(factor_repository)

    async def register_new_factor(
        self,
        factor_name: str,
        factor_expression: str,
        category: str = "custom",
        description: str = "",
        initial_ic: float = 0.0,
    ) -> str:
        """Register a new factor from FactorMiner.

        Args:
            factor_name: Factor name
            factor_expression: Factor expression
            category: Factor category
            description: Factor description
            initial_ic: Initial IC value (if known)

        Returns:
            Factor ID
        """
        factor_id = await self._factor_service.register_factor(
            factor_name=factor_name,
            factor_expression=factor_expression,
            category=category,
            description=description,
        )

        logger.info(f"Registered new factor: {factor_name} ({factor_id})")
        return factor_id

    async def update_daily_ic(
        self,
        factor_id: str,
        calc_date: str,
        ic_value: float,
        rank_ic: float | None = None,
        forward_return: float = 0.0,
        sample_count: int = 0,
    ) -> None:
        """Update daily IC value for a factor.

        This should be called daily after market close.

        Args:
            factor_id: Factor ID
            calc_date: Calculation date (YYYY-MM-DD)
            ic_value: IC value
            rank_ic: Rank IC value (optional)
            forward_return: Forward return
            sample_count: Sample count
        """
        await self._repo.add_ic_record(
            factor_id=factor_id,
            calc_date=calc_date,
            ic_value=ic_value,
            rank_ic=rank_ic,
            forward_return=forward_return,
            sample_count=sample_count,
        )

        logger.debug(f"Updated daily IC for {factor_id}: {ic_value:.4f} on {calc_date}")

    async def evaluate_factor_health(self, factor_id: str) -> dict[str, Any]:
        """Evaluate factor health and determine state transition.

        Args:
            factor_id: Factor ID

        Returns:
            Evaluation result with recommended action
        """
        factor = await self._repo.get_factor(factor_id)
        if not factor:
            return {"action": "not_found", "reason": "factor_not_found"}

        ic_history = await self._repo.get_ic_history(
            factor_id,
            days=self._config.LOOKBACK_DAYS,
        )

        if len(ic_history) < self._config.CONSECUTIVE_DAYS_BELOW_THRESHOLD:
            return {
                "action": "insufficient_data",
                "reason": f"need_{self._config.CONSECUTIVE_DAYS_BELOW_THRESHOLD}_days",
            }

        recent_ic_values = [r["ic_value"] for r in ic_history[-self._config.CONSECUTIVE_DAYS_BELOW_THRESHOLD:]]
        historical_ic = [r["ic_value"] for r in ic_history]

        recent_mean = np.mean(recent_ic_values)
        historical_mean = np.mean(historical_ic)
        ic_std = np.std(historical_ic)
        ir = historical_mean / ic_std if ic_std > 0 else 0.0

        consecutive_below_threshold = sum(
            1 for ic in recent_ic_values if abs(ic) < self._config.IC_THRESHOLD_ACTIVE
        )

        decay_result = await self._factor_service.detect_decay(
            factor_id,
            lookback_days=self._config.LOOKBACK_DAYS,
            decay_threshold=self._config.DECAY_THRESHOLD_WARNING,
        )

        current_state = factor.get("status", "active")
        recommended_state = self._determine_recommended_state(
            current_state=current_state,
            recent_mean=recent_mean,
            historical_mean=historical_mean,
            ir=ir,
            consecutive_below_threshold=consecutive_below_threshold,
            decay_detected=decay_result.get("detected", False),
            decay_ratio=decay_result.get("decay_ratio", 0.0),
        )

        return {
            "factor_id": factor_id,
            "factor_name": factor.get("factor_name"),
            "current_state": current_state,
            "recommended_state": recommended_state,
            "recent_ic_mean": recent_mean,
            "historical_ic_mean": historical_mean,
            "ir": ir,
            "consecutive_below_threshold": consecutive_below_threshold,
            "decay_detected": decay_result.get("detected", False),
            "decay_ratio": decay_result.get("decay_ratio", 0.0),
            "action_required": current_state != recommended_state,
        }

    def _determine_recommended_state(
        self,
        current_state: str,
        recent_mean: float,
        historical_mean: float,
        ir: float,
        consecutive_below_threshold: int,
        decay_detected: bool,
        decay_ratio: float,
    ) -> str:
        """Determine recommended state based on metrics.

        State transitions:
        - active -> monitoring: IC drops below threshold or decay detected
        - monitoring -> deprecated: IC stays below threshold for N days
        - deprecated -> archived: After 30 days in deprecated state
        """
        if current_state == FactorState.ARCHIVED.value:
            return FactorState.ARCHIVED.value

        if current_state == FactorState.DEPRECATED.value:
            return FactorState.ARCHIVED.value

        if current_state == FactorState.MONITORING.value:
            if (
                consecutive_below_threshold >= self._config.CONSECUTIVE_DAYS_BELOW_THRESHOLD
                or abs(recent_mean) < self._config.IC_THRESHOLD_MONITORING
            ):
                return FactorState.DEPRECATED.value
            elif abs(recent_mean) >= self._config.IC_THRESHOLD_ACTIVE:
                return FactorState.ACTIVE.value
            return FactorState.MONITORING.value

        if current_state == FactorState.ACTIVE.value:
            if (
                decay_detected and decay_ratio > self._config.DECAY_THRESHOLD_CRITICAL
            ) or ir < self._config.IR_THRESHOLD:
                return FactorState.MONITORING.value
            return FactorState.ACTIVE.value

        return FactorState.ACTIVE.value

    async def execute_state_transition(
        self,
        factor_id: str,
        new_state: str,
        reason: str = "",
    ) -> bool:
        """Execute factor state transition.

        Args:
            factor_id: Factor ID
            new_state: New state
            reason: Reason for transition

        Returns:
            True if transition successful
        """
        factor = await self._repo.get_factor(factor_id)
        if not factor:
            return False

        current_state = factor.get("status", "active")
        if current_state == new_state:
            return True

        if new_state == FactorState.DEPRECATED.value:
            success = await self._repo.deactivate_factor(factor_id, reason=reason)
            logger.warning(f"Factor {factor_id} deprecated: {reason}")
            return success

        if new_state == FactorState.MONITORING.value:
            await self._repo.update_factor_performance(
                factor_id=factor_id,
                ic_mean=factor.get("ic_mean", 0.0),
                ic_std=factor.get("ic_std", 0.0),
                ir=factor.get("ir", 0.0),
                decay_rate=factor.get("decay_rate", 0.0),
            )
            logger.info(f"Factor {factor_id} moved to monitoring: {reason}")
            return True

        return False

    async def run_daily_lifecycle_check(self) -> dict[str, Any]:
        """Run daily lifecycle check for all active factors.

        This should be called daily after market close via Celery task.

        Returns:
            Summary of lifecycle check results
        """
        active_factors = await self._repo.list_factors(
            status="active",
            limit=1000,
        )

        monitoring_factors = await self._repo.list_factors(
            status="monitoring",
            limit=100,
        )

        results = {
            "evaluated": 0,
            "transitions": 0,
            "deprecated": 0,
            "errors": 0,
        }

        for factor in active_factors + monitoring_factors:
            try:
                factor_id = factor.get("factor_id")
                if not factor_id:
                    continue

                evaluation = await self.evaluate_factor_health(factor_id)

                if evaluation.get("action_required"):
                    recommended_state = evaluation.get("recommended_state")
                    success = await self.execute_state_transition(
                        factor_id,
                        recommended_state,
                        reason=f"Auto-transition: IC={evaluation.get('recent_ic_mean', 0):.4f}, IR={evaluation.get('ir', 0):.4f}",
                    )

                    if success:
                        results["transitions"] += 1
                        if recommended_state == FactorState.DEPRECATED.value:
                            results["deprecated"] += 1

                results["evaluated"] += 1

            except Exception as e:
                logger.error(f"Error evaluating factor {factor.get('factor_id')}: {e}")
                results["errors"] += 1

        logger.info(
            f"Daily lifecycle check: evaluated={results['evaluated']}, "
            f"transitions={results['transitions']}, deprecated={results['deprecated']}"
        )

        return results

    async def get_active_factors(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get list of active factors.

        Args:
            category: Optional category filter

        Returns:
            List of active factors
        """
        return await self._repo.list_factors(
            category=category,
            status="active",
            order_by="ir",
            limit=1000,
        )

    async def get_deprecated_factors(self) -> list[dict[str, Any]]:
        """Get list of deprecated factors.

        Returns:
            List of deprecated factors
        """
        return await self._repo.list_factors(
            status="deprecated",
            order_by="updated",
            limit=100,
        )


__all__ = [
    "FactorLifecycleManager",
    "FactorLifecycleConfig",
    "FactorState",
]
