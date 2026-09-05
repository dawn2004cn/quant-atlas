from __future__ import annotations

"""Quant capability kernel API — tearsheet / factor IC / HRP."""

from flask import Blueprint, jsonify, request

from app.core.registry import register_routes
from app.domain.quant.factor_diagnostics import diagnose_factor
from app.domain.quant.hrp import hrp_weights
from app.domain.quant.tearsheet import compute_tearsheet
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response


def _bad_request(message: str):
    payload = error_payload(ErrorCode.VALIDATION_ERROR, message)
    return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status


@register_routes(name="quant_capability", context="strategy", description="QuantStats/Alphalens/HRP kernel")
def register_quant_capability_routes(blueprint: Blueprint, ctx) -> None:
    _ = ctx
    quant_bp = Blueprint("quant_capability", __name__, url_prefix="/quant")

    @quant_bp.post("/tearsheet")
    def tearsheet():
        body = request.get_json(silent=True) or {}
        returns = body.get("returns")
        if not isinstance(returns, list) or not returns:
            return _bad_request("returns must be a non-empty list")
        dates = body.get("dates")
        return success_response(data=compute_tearsheet(returns, dates=dates))

    @quant_bp.post("/factor-diagnostics")
    def factor_diagnostics():
        body = request.get_json(silent=True) or {}
        factor = body.get("factor") or body.get("factor_values")
        fwd = body.get("forward_returns")
        if factor is None or fwd is None:
            return _bad_request("factor and forward_returns are required")
        n_quantiles = int(body.get("n_quantiles") or 5)
        return success_response(data=diagnose_factor(factor, fwd, n_quantiles=n_quantiles))

    @quant_bp.post("/hrp")
    def allocate_hrp():
        body = request.get_json(silent=True) or {}
        returns = body.get("returns")
        if not isinstance(returns, dict) or not returns:
            return _bad_request("returns must be a non-empty {symbol: [float]} map")
        return success_response(data={"weights": hrp_weights(returns)})

    blueprint.register_blueprint(quant_bp)
