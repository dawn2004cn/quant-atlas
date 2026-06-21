"""Portfolio API sub-package."""

from app.presentation.api.v1.portfolio.core_routes import register_portfolio_core_routes
from app.presentation.api.v1.portfolio.detail_routes import register_portfolio_detail_routes
from app.presentation.api.v1.portfolio.trade_routes import register_portfolio_trade_routes

__all__ = [
    "register_portfolio_core_routes",
    "register_portfolio_detail_routes",
    "register_portfolio_trade_routes",
]
