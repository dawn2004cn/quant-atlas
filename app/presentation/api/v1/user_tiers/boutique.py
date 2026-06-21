"""User Tier API — Boutique tier routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.core.registry import register_routes
from app.presentation.api.v1.user_tiers._http import tier_not_found, tier_success

_bp = Blueprint("boutique", __name__)


def _get_services():
    from app.modules.strategy.services.boutique_tier_service import (
        VectorizedBacktestService, AltDataConnectorService, CollaborativeLabService,
    )
    return VectorizedBacktestService(), AltDataConnectorService(), CollaborativeLabService()


# ── Vectorized Backtest ──

@_bp.post("/boutique/backtest/run")
@login_required
def boutique_backtest():
    data = request.get_json(silent=True) or {}
    svc, _, _ = _get_services()
    result = svc.run(
        strategy_id=str(data.get("strategy_id", "")),
        returns=data.get("returns", []),
        signals=data.get("signals", []),
        params=data.get("params"),
        backend=str(data.get("backend", "auto")),
    )
    return tier_success(result)


@_bp.post("/boutique/backtest/grid-search")
@login_required
def boutique_grid_search():
    data = request.get_json(silent=True) or {}
    svc, _, _ = _get_services()
    param_grid = data.get("param_grid", {})
    results = svc.grid_search(
        strategy_id=str(data.get("strategy_id", "")),
        returns=data.get("returns", []),
        param_grid=param_grid,
        signal_fn=lambda ret, params: [ret[i] * params.get("scale", 1) for i in range(len(ret))],
    )
    return tier_success([r for r in results])


# ── Alternative Data ──

@_bp.get("/boutique/alt-data/sources")
@login_required
def boutique_alt_sources():
    _, svc, _ = _get_services()
    sources = svc.list_sources()
    return tier_success([s for s in sources])


@_bp.get("/boutique/alt-data/fetch/<source_id>/<symbol>")
@login_required
def boutique_alt_fetch(source_id: str, symbol: str):
    _, svc, _ = _get_services()
    point = svc.fetch(source_id, symbol)
    if point:
        return tier_success(point)
    return tier_not_found("source not found")


# ── Collaborative Lab ──

@_bp.post("/boutique/collab/notebook")
@login_required
def boutique_collab_notebook():
    data = request.get_json(silent=True) or {}
    _, _, svc = _get_services()
    nb = svc.create_notebook(
        team_id=int(data.get("team_id", 0)),
        title=str(data.get("title", "")),
        content=str(data.get("content", "")),
        created_by=current_user.id,
        tags=data.get("tags", []),
    )
    return tier_success(nb)


@_bp.post("/boutique/collab/share-factor")
@login_required
def boutique_collab_share_factor():
    data = request.get_json(silent=True) or {}
    _, _, svc = _get_services()
    factor = svc.share_factor(
        team_id=int(data.get("team_id", 0)),
        expression=str(data.get("expression", "")),
        shared_by=current_user.id,
        ic_history=data.get("ic_history"),
    )
    return tier_success(factor)


# ── Factor Mining ──

@_bp.post("/boutique/factor-mining/run")
@login_required
def boutique_factor_mining():
    """Genetic factor discovery for quant boutique teams."""
    data = request.get_json(silent=True) or {}
    from app.modules.strategy.services.alpha_mining_service import AutoAlphaMiningService
    svc = AutoAlphaMiningService()
    generations = int(data.get("generations", 5))
    population_size = int(data.get("population_size", 30))
    svc.seed_population(size=population_size)

    def _fitness(expr: str) -> float:
        return len(expr) * 0.01 + 0.5

    for _ in range(generations):
        svc.evolve(fitness_fn=_fitness, population_size=population_size)
    top = svc.get_top_factors(5)
    return tier_success(
        {
            "generations_run": generations,
            "population_size": population_size,
            "top_factors": [
                {
                    "factor_id": f.factor_id,
                    "expression": f.expression,
                    "ic_mean": f.ic_mean,
                    "sharpe": f.sharpe,
                    "complexity": f.complexity,
                }
                for f in top
            ],
        }
    )


@_bp.post("/boutique/factor-mining/evolve")
@login_required
def boutique_factor_mining_evolve():
    """GP evolution for auto factor mining."""
    data = request.get_json(silent=True) or {}
    from app.modules.strategy.services.boutique_tier_service import AutoFactorMiningService
    svc = AutoFactorMiningService()
    data_matrix = data.get("data", [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8], [0.9, 1.0]])
    returns = data.get("returns", [0.01, 0.02, -0.01, 0.03, 0.02])
    pop_size = int(data.get("population_size", 30))
    gens = int(data.get("generations", 10))
    result = svc.run_evolution(data_matrix, returns, population_size=pop_size, generations=gens)
    return tier_success(result)


@_bp.post("/boutique/factor-mining/save")
@login_required
def boutique_factor_mining_save():
    data = request.get_json(silent=True) or {}
    from app.modules.strategy.services.boutique_tier_service import AutoFactorMiningService
    svc = AutoFactorMiningService()
    saved = svc.save_factor(
        name=str(data.get("name", "")),
        expression=str(data.get("expression", "")),
        ic=float(data.get("ic", 0)),
        created_by=str(data.get("created_by", current_user.id)),
    )
    return tier_success(saved)


@_bp.get("/boutique/factor-mining/factors")
@login_required
def boutique_factor_mining_list():
    from app.modules.strategy.services.boutique_tier_service import AutoFactorMiningService
    svc = AutoFactorMiningService()
    min_ic = request.args.get("min_ic", 0, type=float)
    factors = svc.list_factors(min_ic=min_ic)
    return tier_success(factors)


# ── Registration ──

@register_routes(name="boutique", context="system", description="Boutique tier: Backtest, Alt Data, Collab, Factor Mining")
def register_boutique_routes(blueprint, ctx) -> None:
    blueprint.register_blueprint(_bp, url_prefix="/user-tiers")
