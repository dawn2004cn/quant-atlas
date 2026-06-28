from __future__ import annotations
"""Inline Risk Middleware - Execution Interceptor.

This module implements from strategy_plan1.md:
- ExecutionInterceptor: Microsecond-level risk validation
- Position limits, leverage check, liquidity validation
- Pre-trade risk checks before order execution

Usage:
    interceptor = ExecutionInterceptor()
    result = interceptor.validate_order(order, portfolio_state)
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    approved: bool
    rejected_reason: str | None = None
    risk_level: str = "normal"
    adjusted_order: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_per_symbol: float = 0.2
    max_total_leverage: float = 1.5
    max_daily_turnover: float = 2.0
    max_price_deviation: float = 0.05
    max_correlation_exposure: float = 0.6
    min_liquidity_ratio: float = 0.3


class PositionLimitChecker:
    """Check position concentration limits."""

    def __init__(self, limits: RiskLimits):
        self._limits = limits

    def check(
        self,
        symbol: str,
        order_value: float,
        current_positions: dict[str, float],
        portfolio_value: float,
    ) -> RiskCheckResult:
        """Check single position concentration."""
        if portfolio_value <= 0:
            return RiskCheckResult(approved=True)

        current_exposure = current_positions.get(symbol, 0)
        new_exposure = current_exposure + order_value

        if new_exposure / portfolio_value > self._limits.max_position_per_symbol:
            max_allowed = portfolio_value * self._limits.max_position_per_symbol
            adjusted_value = max(0, max_allowed - current_exposure)

            if adjusted_value > 0:
                return RiskCheckResult(
                    approved=True,
                    adjusted_order={"order_value": adjusted_value},
                    risk_level="warning",
                )
            else:
                return RiskCheckResult(
                    approved=False,
                    rejected_reason=f"Position limit exceeded for {symbol}",
                    risk_level="high",
                )

        return RiskCheckResult(approved=True)


class LeverageChecker:
    """Check total account leverage."""

    def __init__(self, limits: RiskLimits):
        self._limits = limits

    def check(
        self,
        order_value: float,
        current_positions: dict[str, float],
        cash_available: float,
    ) -> RiskCheckResult:
        """Check total leverage."""
        total_exposure = sum(current_positions.values()) + order_value
        total_equity = total_exposure + cash_available

        if total_equity <= 0:
            return RiskCheckResult(
                approved=False,
                rejected_reason="Insufficient equity",
                risk_level="critical",
            )

        leverage = total_exposure / total_equity

        if leverage > self._limits.max_total_leverage:
            return RiskCheckResult(
                approved=False,
                rejected_reason=f"Total leverage {leverage:.2f} exceeds limit {self._limits.max_total_leverage}",
                risk_level="high",
            )

        return RiskCheckResult(approved=True)


class TurnoverChecker:
    """Check daily turnover limits."""

    def __init__(self, limits: RiskLimits):
        self._limits = limits

    def check(
        self,
        order_value: float,
        daily_turnover: float,
        portfolio_value: float,
    ) -> RiskCheckResult:
        """Check daily turnover limit."""
        if portfolio_value <= 0:
            return RiskCheckResult(approved=True)

        new_turnover = daily_turnover + order_value
        turnover_ratio = new_turnover / portfolio_value

        if turnover_ratio > self._limits.max_daily_turnover:
            return RiskCheckResult(
                approved=False,
                rejected_reason=f"Daily turnover {turnover_ratio:.2f} exceeds limit {self._limits.max_daily_turnover}",
                risk_level="medium",
            )

        return RiskCheckResult(approved=True)


class LiquidityChecker:
    """Check liquidity and price deviation."""

    def __init__(self, limits: RiskLimits):
        self._limits = limits

    def check(
        self,
        symbol: str,
        order_value: float,
        market_data: dict[str, Any],
    ) -> RiskCheckResult:
        """Check liquidity ratio and price deviation."""
        avg_volume = market_data.get("avg_volume", float("inf"))
        daily_volume = market_data.get("daily_volume", avg_volume)

        if daily_volume <= 0:
            return RiskCheckResult(
                approved=False,
                rejected_reason=f"No volume data for {symbol}",
                risk_level="high",
            )

        participation_rate = order_value / daily_volume if daily_volume > 0 else 0

        if participation_rate > (1 - self._limits.min_liquidity_ratio):
            return RiskCheckResult(
                approved=False,
                rejected_reason=f"Order size {participation_rate:.2%} exceeds liquidity for {symbol}",
                risk_level="high",
            )

        last_price = market_data.get("last_price", 0)
        fair_price = market_data.get("fair_price", last_price)

        if last_price > 0 and fair_price > 0:
            deviation = abs(last_price - fair_price) / fair_price

            if deviation > self._limits.max_price_deviation:
                return RiskCheckResult(
                    approved=False,
                    rejected_reason=f"Price deviation {deviation:.2%} too high for {symbol}",
                    risk_level="high",
                )

        return RiskCheckResult(approved=True)


class ExecutionInterceptor:
    """Complete execution interceptor with all risk checks."""

    def __init__(
        self,
        limits: RiskLimits | None = None,
    ):
        self._limits = limits or RiskLimits()
        self._position_checker = PositionLimitChecker(self._limits)
        self._leverage_checker = LeverageChecker(self._limits)
        self._turnover_checker = TurnoverChecker(self._limits)
        self._liquidity_checker = LiquidityChecker(self._limits)

    def validate_order(
        self,
        order: dict[str, Any],
        portfolio_state: dict[str, Any],
    ) -> RiskCheckResult:
        """Validate order through all risk checks."""
        symbol = order.get("symbol", "")
        order_value = order.get("value", order.get("price", 0) * order.get("volume", 0))

        positions = portfolio_state.get("positions", {})
        portfolio_value = portfolio_state.get("portfolio_value", 1.0)
        cash = portfolio_state.get("cash", 0)
        daily_turnover = portfolio_state.get("daily_turnover", 0)

        result = self._position_checker.check(
            symbol,
            order_value,
            positions,
            portfolio_value,
        )
        if not result.approved:
            logger.warning(f"Position check failed: {result.rejected_reason}")
            return result

        result = self._leverage_checker.check(
            order_value,
            positions,
            cash,
        )
        if not result.approved:
            logger.warning(f"Leverage check failed: {result.rejected_reason}")
            return result

        result = self._turnover_checker.check(
            order_value,
            daily_turnover,
            portfolio_value,
        )
        if not result.approved:
            logger.warning(f"Turnover check failed: {result.rejected_reason}")
            return result

        market_data = portfolio_state.get("market_data", {}).get(symbol, {})
        if market_data:
            result = self._liquidity_checker.check(
                symbol,
                order_value,
                market_data,
            )
            if not result.approved:
                logger.warning(f"Liquidity check failed: {result.rejected_reason}")
                return result

        return RiskCheckResult(
            approved=True,
            risk_level="low",
        )

    def update_limits(self, **kwargs) -> None:
        """Update risk limits at runtime."""
        for key, value in kwargs.items():
            if hasattr(self._limits, key):
                setattr(self._limits, key, value)


_global_interceptor: ExecutionInterceptor | None = None


def get_execution_interceptor() -> ExecutionInterceptor:
    """Get singleton execution interceptor."""
    global _global_interceptor
    if _global_interceptor is None:
        _global_interceptor = ExecutionInterceptor()
    return _global_interceptor


def reset_execution_interceptor() -> None:
    """Reset singleton (for testing)."""
    global _global_interceptor
    _global_interceptor = None
