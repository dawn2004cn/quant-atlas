"""Portfolio users dispatcher smoke import."""

from __future__ import annotations


def test_portfolio_users_submodules():
    from app.presentation.api.v1.portfolio_users import (
        register_portfolio_stock_group_routes,
        register_portfolio_user_admin_routes,
        register_portfolio_watchlist_routes,
    )

    for fn in (
        register_portfolio_watchlist_routes,
        register_portfolio_stock_group_routes,
        register_portfolio_user_admin_routes,
    ):
        assert callable(fn)


def test_portfolio_users_dispatcher():
    from app.presentation.api.routes_v1_portfolio_users import register_portfolio_user_routes

    assert callable(register_portfolio_user_routes)


def test_factor_dispatcher():
    from app.presentation.api.routes_v1_factor import register_factor_routes

    assert callable(register_factor_routes)
