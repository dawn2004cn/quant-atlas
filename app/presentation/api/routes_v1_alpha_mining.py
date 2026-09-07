"""API v1: Auto-Alpha Mining — genetic factor discovery, orthogonalization, and DAO proposal."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...core.registry import register_routes
from .common import ok_response
from .decorators import demo_endpoint
from .v1_context import ApiV1Context
from .validation import bounded_float, bounded_int, whitelist_str


def _get_svc():
    from app.modules.strategy.services.alpha_mining_service import AutoAlphaMiningService

    return AutoAlphaMiningService()


@register_routes(name="alpha_mining", context="strategy", description="Auto-Alpha Mining — genetic factor discovery and governance")
def register_alpha_mining_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @bp.post("/alpha-mining/run")
    @login_required
    @demo_endpoint
    def alpha_mining_run():
        """Start a mining run: seed population and evolve N generations."""
        body = request.get_json(silent=True) or {}
        svc = _get_svc()
        generations = bounded_int(body.get("generations"), default=10, min_value=1, max_value=100)
        population_size = bounded_int(body.get("population_size"), default=50, min_value=2, max_value=500)

        svc.seed_population(size=population_size)

        features = body.get("features")
        returns = body.get("returns")
        if not isinstance(features, dict):
            features = None
        if not isinstance(returns, list):
            returns = None
        _fitness = svc.make_fitness(features, returns)

        for _ in range(generations):
            svc.evolve(fitness_fn=_fitness, population_size=population_size)

        top = svc.get_top_factors(5)
        return ok_response(
            data={
                "generations_run": generations,
                "population_size": population_size,
                "top_factors": [
                    {
                        "factor_id": f.factor_id,
                        "expression": f.expression,
                        "ic_mean": f.ic_mean,
                        "sharpe": f.sharpe,
                        "complexity": f.complexity,
                        "generation": f.generation,
                    }
                    for f in top
                ],
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.get("/alpha-mining/status")
    @login_required
    def alpha_mining_status():
        """Current mining status."""
        svc = _get_svc()
        return ok_response(
            data=svc.get_mining_status(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.get("/alpha-mining/factors")
    @login_required
    def alpha_mining_factors():
        """List discovered factors with optional filtering."""
        svc = _get_svc()
        min_ic = bounded_float(request.args.get("min_ic"), default=-1.0, min_value=-1.0, max_value=1.0)
        min_sharpe = bounded_float(request.args.get("min_sharpe"), default=-1.0, min_value=-10.0, max_value=10.0)
        raw_max_complexity = request.args.get("max_complexity")
        max_complexity = (
            bounded_int(raw_max_complexity, default=10, min_value=1, max_value=50)
            if raw_max_complexity
            else None
        )
        sort_by = whitelist_str(
            request.args.get("sort_by"),
            default="ic_mean",
            allowed={"ic_mean", "sharpe", "complexity", "generation"},
        )

        factors = svc.list_discovered_factors(
            min_ic=min_ic,
            min_sharpe=min_sharpe,
            max_complexity=max_complexity,
            sort_by=sort_by,
        )
        return ok_response(
            data={"factors": factors, "count": len(factors)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha-mining/factors/<factor_id>/orthogonalize")
    @login_required
    def alpha_mining_orthogonalize(factor_id: str):
        """Orthogonalize a factor against all other discovered factors."""
        svc = _get_svc()
        all_factors = svc.get_top_factors(100)
        target = next((f for f in all_factors if f.factor_id == factor_id), None)
        if target is None:
            from ...application.errors import ValidationError
            raise ValidationError("factor_not_found")

        others = [f for f in all_factors if f.factor_id != factor_id]
        features = (request.get_json(silent=True) or {}).get("features")
        if not isinstance(features, dict):
            features = None
        ortho = svc.orthogonalize([target] + others, features=features)
        return ok_response(
            data={
                "factor_id": factor_id,
                "orthogonalized_count": len(ortho),
                "orthogonalized": [
                    {"factor_id": f.factor_id, "expression": f.expression}
                    for f in ortho
                ],
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha-mining/factors/<factor_id>/propose")
    @login_required
    def alpha_mining_propose(factor_id: str):
        """Propose a factor to the AlphaGovernanceDAO."""
        svc = _get_svc()
        result = svc.propose_to_dao(factor_id)
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha-mining/optimize")
    @login_required
    def alpha_mining_optimize():
        """Optimize factor combination weights."""
        body = request.get_json(silent=True) or {}
        svc = _get_svc()
        factor_ids = body.get("factor_ids", [])
        target_metric = body.get("target_metric", "sharpe")

        all_factors = svc.get_top_factors(200)
        selected = [f for f in all_factors if f.factor_id in factor_ids]
        if not selected:
            # Use all top factors if none specified
            selected = all_factors[:10]

        result = svc.optimize_combination(selected, target_metric=target_metric)
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
