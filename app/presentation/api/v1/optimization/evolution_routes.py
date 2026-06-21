"""Anti-decay evolution strategy routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.optimization.runtime import get_anti_decay_evolution_service
from app.presentation.api.v1_context import ApiV1Context


def register_optimization_evolution_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.post("/evolution/diversity")
    @login_required
    def evolution_diversity():
        data = request.get_json(silent=True) or {}
        factors = data.get("factors", [])
        svc = get_anti_decay_evolution_service()
        scores = svc.rank_by_diversity(factors)
        return success_response(data=[s.__dict__ for s in scores])

    @blueprint.post("/evolution/cycle")
    @login_required
    def evolution_cycle():
        data = request.get_json(silent=True) or {}
        svc = get_anti_decay_evolution_service()
        cycle = svc.evolve_strategy(
            parent_strategy_id=str(data.get("strategy_id", "")),
            live_sharpe=float(data.get("sharpe", 0)),
            feedback=data.get("feedback"),
        )
        return success_response(data=cycle.__dict__)

    @blueprint.get("/evolution/history/<strategy_id>")
    @login_required
    def evolution_history(strategy_id: str):
        svc = get_anti_decay_evolution_service()
        history = svc.get_evolution_history(strategy_id)
        return success_response(data=[h.__dict__ for h in history])

    @blueprint.get("/evolution/survival-rate/<strategy_id>")
    @login_required
    def evolution_survival_rate(strategy_id: str):
        svc = get_anti_decay_evolution_service()
        rate = svc.get_survival_rate(strategy_id)
        return success_response(data={"survival_rate": round(rate, 3)})
