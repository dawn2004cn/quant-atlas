"""User Tier API — Investment company tier routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from app.presentation.api.v1.user_tiers._http import tier_success

_bp = Blueprint("investment", __name__)


def _get_services():
    from app.modules.portfolio_risk.services.investment_tier_service import (
        MultiStrategyOptimizerService, MacroRegimeService, TaxCostOptimizerService, MultiAssetService,
    )
    return MultiStrategyOptimizerService(), MacroRegimeService(), TaxCostOptimizerService(), MultiAssetService()


# ── Optimization ──

@_bp.post("/investment/optimize/risk-parity")
@login_required
def investment_risk_parity():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.risk_parity(data.get("strategies", []))
    return tier_success(result)


@_bp.post("/investment/optimize/black-litterman")
@login_required
def investment_black_litterman():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.black_litterman(
        strategies=data.get("strategies", []),
        views=data.get("views"),
        tau=float(data.get("tau", 0.05)),
    )
    return tier_success(result)


# ── Macro Regime ──

@_bp.post("/investment/macro-regime")
@login_required
def investment_macro_regime():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    regime = svc.analyze(data.get("indicators", {}))
    return tier_success(regime)


@_bp.post("/investment/macro-regime/transition")
@login_required
def investment_macro_transition():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    indicators = data.get("indicators", {})
    prev = data.get("previous_regime")
    result = svc.detect_transition(indicators, prev)
    return tier_success(result)


# ── Tax ──

@_bp.post("/investment/tax-optimize")
@login_required
def investment_tax_optimize():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    report = svc.optimize(
        trades=data.get("trades", []),
        tax_rate=float(data.get("tax_rate", 0.2)),
    )
    return tier_success(report)


@_bp.post("/investment/tax/harvest")
@login_required
def investment_tax_harvest():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    positions = data.get("positions", [])
    max_loss = float(data.get("max_loss_pct", 0.05))
    result = svc.tax_loss_harvesting(positions, max_loss_pct=max_loss)
    return tier_success(result)


# ── Multi-Asset ──

@_bp.post("/investment/multi-asset/hedge")
@login_required
def investment_multi_asset_hedge():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    from app.modules.portfolio_risk.services.investment_tier_service import MultiAssetPosition
    positions = [MultiAssetPosition(**p) for p in data.get("positions", [])]
    result = svc.compute_cross_hedge(positions)
    return tier_success(result)


@_bp.post("/investment/multi-asset/market-neutral")
@login_required
def investment_market_neutral():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    long_pos = data.get("long_positions", [])
    short_pos = data.get("short_positions", [])
    result = svc.market_neutral_hedge(long_pos, short_pos)
    return tier_success(result)


@_bp.post("/investment/multi-asset/currency-hedge")
@login_required
def investment_currency_hedge():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    exposures = data.get("exposures", [])
    base = str(data.get("base_currency", "USD"))
    result = svc.cross_currency_hedge(base, exposures)
    return tier_success(result)


# ── Registration ──

@register_routes(name="investment", context="system", description="Investment company tier: Optimization, Macro, Tax, Multi-Asset")
def register_investment_routes(blueprint, ctx) -> None:
    blueprint.register_blueprint(_bp, url_prefix="/user-tiers")
