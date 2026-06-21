from __future__ import annotations
"""Risk gateway implementations."""


from typing import Any

from ...core.risk_controls import load_default_risk_params, load_default_position_sizing_params
from ...domain.ports.risk_ports import (
    OrderContext,
    PositionSizingPort,
    RiskCheckResult,
    RiskPreFlightPort,
    KellyPositionSizing,
)


class DefaultRiskPreFlight(RiskPreFlightPort):
    """Default risk pre-flight check implementation."""

    def __init__(
        self,
        max_single_position_pct: float = 0.15,
        max_total_position_pct: float = 0.9,
        daily_loss_limit: float = 0.05,
        min_cash_reserve: float = 1000.0,
    ) -> None:
        self._max_single_pct = max_single_position_pct
        self._max_total_pct = max_total_position_pct
        self._daily_loss_limit = daily_loss_limit
        self._min_cash_reserve = min_cash_reserve
        self._risk = load_default_risk_params()
        self._sizing = load_default_position_sizing_params()

    def check_order(self, order: OrderContext) -> RiskCheckResult:
        """Check order against all pre-flight rules."""
        blocked: list[str] = []
        details: dict[str, Any] = {}

        equity = float(order.total_equity)
        position_value = float(order.quantity) * float(order.price)
        position_pct = position_value / equity if equity > 0 else 0

        if position_pct > self._max_single_pct:
            blocked.append("MAX_SINGLE_POSITION")
            details["max_single_pct"] = self._max_single_pct
            details["requested_pct"] = round(position_pct, 4)

        total_exposure = sum(
            float(qty) * float(order.price)
            for symbol, qty in order.current_positions.items()
            if symbol != order.symbol
        )
        total_exposure += position_value
        total_pct = total_exposure / equity if equity > 0 else 0
        if total_pct > self._max_total_pct:
            blocked.append("MAX_TOTAL_POSITION")
            details["max_total_pct"] = self._max_total_pct
            details["total_pct"] = round(total_pct, 4)

        order_cost = position_value
        if order.cash_available < order_cost + self._min_cash_reserve:
            blocked.append("INSUFFICIENT_CASH")
            details["cash_required"] = round(order_cost + self._min_cash_reserve, 2)
            details["cash_available"] = round(order.cash_available, 2)

        daily_loss_pct = abs(order.daily_pnl) / equity if equity > 0 else 0
        if daily_loss_pct > self._daily_loss_limit:
            blocked.append("DAILY_LOSS_LIMIT")
            details["daily_loss_limit"] = self._daily_loss_limit
            details["daily_loss_pct"] = round(daily_loss_pct, 4)

        if order.quantity <= 0:
            blocked.append("INVALID_QUANTITY")

        if order.price <= 0:
            blocked.append("INVALID_PRICE")

        if blocked:
            return RiskCheckResult.fail(
                reason=f"Risk blocked: {', '.join(blocked)}",
                blocked_rules=blocked,
                details=details,
            )
        return RiskCheckResult.pass_()

    def check_portfolio_risk(self, orders: list[OrderContext]) -> RiskCheckResult:
        """Check portfolio-level risk across orders."""
        equity = float(orders[0].total_equity) if orders else 0
        total_cost = sum(float(o.quantity) * float(o.price) for o in orders)
        total_pct = total_cost / equity if equity > 0 else 0

        if total_pct > self._max_total_pct:
            return RiskCheckResult.fail(
                reason="Total portfolio exposure exceeds limit",
                blocked_rules=["MAX_TOTAL_POSITION"],
                details={"total_pct": round(total_pct, 4), "max_pct": self._max_total_pct},
            )

        symbols = [o.symbol for o in orders]
        if len(symbols) != len(set(symbols)):
            return RiskCheckResult.fail(
                reason="Duplicate symbols in batch orders",
                blocked_rules=["DUPLICATE_SYMBOL"],
            )

        return RiskCheckResult.pass_()


class DefaultPositionSizing(PositionSizingPort):
    """Default position sizing using Kelly Criterion and Volatility Targeting."""

    def __init__(self, max_position_pct: float = 0.2) -> None:
        self._max_pct = max_position_pct

    def compute_kelly(self, win_rate: float, payoff_ratio: float, *, fraction: float = 0.5) -> KellyPositionSizing:
        if payoff_ratio <= 0 or win_rate <= 0 or win_rate >= 1:
            kelly = 0.0
        else:
            q = 1.0 - win_rate
            kelly = (win_rate * payoff_ratio - q) / payoff_ratio
            kelly = max(0.0, min(kelly, 1.0))

        return KellyPositionSizing(
            kelly_fraction=round(kelly * fraction, 4),
            recommended_shares=0,
            max_shares=0,
            risk_per_trade=round(kelly * fraction, 4),
            edge=win_rate,
            payoff_ratio=payoff_ratio,
        )

    def compute_vol_target(self, equity: float, volatility: float, target_vol: float = 0.15) -> float:
        if volatility <= 0:
            return float(equity * self._max_pct)
        vol_ratio = target_vol / volatility
        position = float(equity) * min(vol_ratio, self._max_pct)
        return max(0.0, position)