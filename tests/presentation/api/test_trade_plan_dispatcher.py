"""Trade plan dispatcher smoke import."""

from __future__ import annotations


def test_trade_plan_submodules_export_register_functions():
    from app.presentation.api.v1.trade_plan import (
        register_decision_review_routes,
        register_trade_plan_core_routes,
        register_trade_review_routes,
    )

    for fn in (
        register_trade_plan_core_routes,
        register_trade_review_routes,
        register_decision_review_routes,
    ):
        assert callable(fn)


def test_trade_plan_dispatcher_registers():
    from app.presentation.api.routes_v1_trade_plan import register_trade_plan_routes

    assert callable(register_trade_plan_routes)
