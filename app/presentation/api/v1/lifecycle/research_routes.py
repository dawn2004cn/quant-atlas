"""Lifecycle research-layer routes (alpha mining, sensitivity, cross-sectional)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.lifecycle.runtime import get_alpha_mining_services
from app.presentation.api.v1_context import ApiV1Context


def register_lifecycle_research_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @blueprint.post("/alpha-mine/seed")
    @login_required
    def alpha_mine_seed():
        svc, _, _ = get_alpha_mining_services()
        svc.seed_population()
        return success_response(data={"population": len(svc._population)})

    @blueprint.post("/alpha-mine/evolve")
    @login_required
    def alpha_mine_evolve():
        svc, _, _ = get_alpha_mining_services()
        svc.evolve(lambda expr: hash(expr) % 1000 / 1000.0)
        top = svc.get_top_factors(5)
        return success_response(
            data={"generation": svc._generation, "top": [f.__dict__ for f in top]},
        )

    @blueprint.post("/parameter-sensitivity")
    @login_required
    def parameter_sensitivity():
        _, svc, _ = get_alpha_mining_services()
        data = request.get_json(silent=True) or {}
        report = svc.analyze(
            strategy_id=str(data.get("strategy_id", "")),
            param_name=str(data.get("param_name", "")),
            param_range=data.get("param_range", []),
            performance_fn=lambda v: 1.0 - abs(v - 0.5) * 2,
        )
        return success_response(data=report.__dict__)

    @blueprint.post("/cross-sectional/rank")
    @login_required
    def cross_sectional_rank():
        _, _, svc = get_alpha_mining_services()
        data = request.get_json(silent=True) or {}
        result = svc.rank_stocks(
            timestamp=str(data.get("timestamp", "")),
            stocks=data.get("stocks", []),
            factor_fn=lambda s: float(s.get("score", hash(str(s.get("symbol", ""))) % 100)),
        )
        return success_response(data=result.__dict__)
