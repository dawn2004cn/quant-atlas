"""Lifecycle simulation-layer routes (LOB, walk-forward, Monte Carlo)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.lifecycle.runtime import get_simulation_services
from app.presentation.api.v1_context import ApiV1Context


def register_lifecycle_simulation_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @blueprint.post("/sim/lob")
    @login_required
    def sim_lob():
        svc, _, _ = get_simulation_services()
        data = request.get_json(silent=True) or {}
        lob = svc.simulate_lob(
            symbol=str(data.get("symbol", "")),
            base_price=float(data.get("base_price", 100)),
        )
        return success_response(data=lob.__dict__)

    @blueprint.post("/sim/market-impact")
    @login_required
    def sim_market_impact():
        svc, _, _ = get_simulation_services()
        data = request.get_json(silent=True) or {}
        from app.modules.strategy.services.simulation_service import LimitOrderBook

        lob = LimitOrderBook(**data.get("lob", {}))
        result = svc.estimate_market_impact(
            symbol=str(data.get("symbol", "")),
            order_quantity=int(data.get("quantity", 1000)),
            side=str(data.get("side", "buy")),
            lob=lob,
        )
        return success_response(data=result.__dict__)

    @blueprint.post("/sim/walk-forward")
    @login_required
    def sim_walk_forward():
        _, svc, _ = get_simulation_services()
        data = request.get_json(silent=True) or {}
        result = svc.validate(
            strategy_id=str(data.get("strategy_id", "")),
            returns=data.get("returns", []),
        )
        return success_response(data=result.__dict__)

    @blueprint.post("/sim/monte-carlo")
    @login_required
    def sim_monte_carlo():
        _, _, svc = get_simulation_services()
        data = request.get_json(silent=True) or {}
        result = svc.stress_test(
            strategy_id=str(data.get("strategy_id", "")),
            historical_returns=data.get("returns", []),
            iterations=int(data.get("iterations", 1000)),
        )
        return success_response(data=result.__dict__)
