"""Unified trading risk facade for API routes and trade-plan checks."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.domain.ports.risk_ports import OrderContext, PositionSizingPort, RiskPreFlightPort
from app.modules.system.services.helpers.trading_risk_access import (
    create_default_position_sizing,
    create_default_risk_preflight,
)


def _resolve_preflight() -> RiskPreFlightPort:
    try:
        return create_default_risk_preflight()
    except RuntimeError:
        from app.infrastructure.risk.risk_gateway import DefaultRiskPreFlight

        return DefaultRiskPreFlight()


def _resolve_sizing() -> PositionSizingPort:
    try:
        return create_default_position_sizing()
    except RuntimeError:
        from app.infrastructure.risk.risk_gateway import DefaultPositionSizing

        return DefaultPositionSizing()


class TradingRiskFacade:
    """Expose route-friendly risk methods backed by domain ports."""

    def __init__(
        self,
        *,
        preflight: RiskPreFlightPort | None = None,
        sizing: PositionSizingPort | None = None,
        default_volatility: float = 0.25,
    ) -> None:
        self._preflight = preflight or _resolve_preflight()
        self._sizing = sizing or _resolve_sizing()
        self._default_volatility = default_volatility

    @staticmethod
    def _order_from_mapping(data: dict[str, Any]) -> OrderContext:
        total_equity = float(data.get("total_equity") or 100_000.0)
        return OrderContext(
            symbol=str(data.get("symbol") or "").strip().upper(),
            side=str(data.get("side") or "buy").strip().lower(),
            quantity=int(data.get("quantity") or 0),
            price=float(data.get("price") or 0.0),
            account_id=str(data.get("account_id") or "default"),
            total_equity=total_equity,
            cash_available=float(data.get("cash_available") if data.get("cash_available") is not None else total_equity),
            current_positions=dict(data.get("current_positions") or {}),
            daily_pnl=float(data.get("daily_pnl") or 0.0),
            market=str(data.get("market") or "CN"),
        )

    def check_order(self, **kwargs: Any):
        """Pre-flight check for a single order (returns ``RiskCheckResult``)."""
        return self._preflight.check_order(self._order_from_mapping(kwargs))

    def check_orders_batch(self, orders: list[dict[str, Any]]):
        """Batch pre-flight checks for multiple orders."""
        contexts = [self._order_from_mapping(item) for item in orders if isinstance(item, dict)]
        portfolio = self._preflight.check_portfolio_risk(contexts) if contexts else None
        checks = [self._preflight.check_order(ctx) for ctx in contexts]
        return {
            "portfolio_allowed": portfolio.allowed if portfolio else True,
            "portfolio_reason": portfolio.reason if portfolio else "PASS",
            "portfolio_blocked_rules": portfolio.blocked_rules if portfolio else [],
            "orders": [asdict(result) for result in checks],
        }

    def compute_volatility_target_position(
        self,
        *,
        symbol: str,
        target_vol: float,
        lookback: int,
        total_equity: float,
        volatility: float | None = None,
        **_: Any,
    ) -> float:
        """Volatility-target position size in currency units."""
        _ = symbol, lookback
        vol = float(volatility if volatility is not None else self._default_volatility)
        return self._sizing.compute_vol_target(float(total_equity), vol, float(target_vol))

    def compute_kelly_position(
        self,
        *,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        total_equity: float,
        fraction: float = 0.25,
        **_: Any,
    ) -> float:
        """Kelly fraction (0–1), not dollar amount."""
        _ = total_equity
        payoff = float(avg_win) / float(avg_loss) if float(avg_loss) > 0 else 0.0
        sizing = self._sizing.compute_kelly(float(win_rate), payoff, fraction=float(fraction))
        return float(sizing.kelly_fraction)


__all__ = ["TradingRiskFacade"]
