"""Portfolio & Risk module routes — API entrypoints for portfolio / risk / trade-plan."""

from __future__ import annotations

from app.presentation.api.routes_v1_portfolio import register_portfolio_routes
from app.presentation.api.routes_v1_risk import register_risk_routes
from app.presentation.api.routes_v1_trade_plan import register_trade_plan_routes

__all__ = [
    "register_portfolio_routes",
    "register_risk_routes",
    "register_trade_plan_routes",
]
