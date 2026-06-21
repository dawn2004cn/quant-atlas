"""Portfolio routes dispatcher smoke import."""

from __future__ import annotations


def test_portfolio_submodules_export_register_functions():
    from app.presentation.api.v1.portfolio import (
        register_portfolio_core_routes,
        register_portfolio_detail_routes,
        register_portfolio_trade_routes,
    )

    assert callable(register_portfolio_core_routes)
    assert callable(register_portfolio_detail_routes)
    assert callable(register_portfolio_trade_routes)


def test_portfolio_dispatcher_registers():
    from app.presentation.api.routes_v1_portfolio import register_portfolio_routes

    assert callable(register_portfolio_routes)
