"""Zen mode API routes — focus mode, resonance field, strategy vault, watermark, adaptive complexity."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _get_zen_service():
    from app.modules.system.services.zen_mode_service import ZenModeService

    return ZenModeService()


def _get_resonance_service():
    from app.modules.system.services.resonance_field_service import PortfolioResonanceFieldService

    return PortfolioResonanceFieldService()


def _get_vault_service():
    from app.modules.system.services.strategy_vault_service import StrategyVaultService

    return StrategyVaultService()


def _get_watermark_service():
    from app.modules.system.services.strategy_vault_service import TruthWatermarkService

    return TruthWatermarkService()


def _get_complexity_service():
    from app.modules.system.services.adaptive_complexity_service import AdaptiveComplexityService

    return AdaptiveComplexityService()


def _validation_error(message: str):
    payload = error_payload(ErrorCode.VALIDATION_ERROR, message)
    return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status


def _register_zen_mode_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx
    zen_bp = Blueprint("zen_mode", __name__, url_prefix="/zen-mode")

    @zen_bp.get("/zen/config")
    @login_required
    def zen_config():
        config = _get_zen_service().get_config(current_user.id)
        return success_response(data=config)

    @zen_bp.post("/zen/toggle")
    @login_required
    def zen_toggle():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", True))
        config = _get_zen_service().set_zen_mode(current_user.id, enabled)
        return success_response(data=config)

    @zen_bp.post("/zen/search")
    @login_required
    def zen_search():
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "")).strip()
        if not query:
            return _validation_error("query required")
        results = _get_zen_service().semantic_search(query, current_user.id)
        return success_response(
            data={
                "query": query,
                "results": results,
            },
        )

    @zen_bp.post("/zen/evolve")
    @login_required
    def zen_evolve():
        data = request.get_json(silent=True) or {}
        days_active = int(data.get("days_active", 0))
        total_actions = int(data.get("total_actions", 0))
        config = _get_zen_service().evolve_complexity(current_user.id, days_active, total_actions)
        return success_response(data=config)

    @zen_bp.post("/resonance/field")
    @login_required
    def resonance_field():
        data = request.get_json(silent=True) or {}
        holdings = data.get("holdings", [])
        regime = str(data.get("regime", "bull"))
        state = _get_resonance_service().compute_field(holdings, regime)
        return success_response(
            data={
                "particles": state.particles,
                "crowding_warnings": state.crowding_warnings,
                "diversity_score": state.diversity_score,
                "last_updated": state.last_updated,
            },
        )

    @zen_bp.post("/vault/fingerprint")
    @login_required
    def vault_fingerprint():
        data = request.get_json(silent=True) or {}
        strategy_id = str(data.get("strategy_id", ""))
        strategy_logic = str(data.get("strategy_logic", ""))
        if not strategy_id:
            return _validation_error("strategy_id required")
        fp = _get_vault_service().fingerprint_strategy(strategy_id, current_user.id, strategy_logic)
        return success_response(data=fp)

    @zen_bp.post("/vault/verify")
    @login_required
    def vault_verify():
        data = request.get_json(silent=True) or {}
        strategy_id = str(data.get("strategy_id", ""))
        strategy_logic = str(data.get("strategy_logic", ""))
        if not strategy_id:
            return _validation_error("strategy_id required")
        valid = _get_vault_service().verify_fingerprint(strategy_id, current_user.id, strategy_logic)
        return success_response(data={"valid": valid})

    @zen_bp.post("/watermark/generate")
    @login_required
    def watermark_generate():
        data = request.get_json(silent=True) or {}
        symbol = str(data.get("symbol", ""))
        market = str(data.get("market", "CN"))
        payload = data.get("payload", {})
        if not symbol:
            return _validation_error("symbol required")
        wm = _get_watermark_service().generate_watermark(symbol, market, payload)
        return success_response(data=wm)

    @zen_bp.post("/watermark/verify")
    @login_required
    def watermark_verify():
        data = request.get_json(silent=True) or {}
        watermark_b64 = str(data.get("watermark_b64", ""))
        payload = data.get("payload", {})
        if not watermark_b64:
            return _validation_error("watermark_b64 required")
        result = _get_watermark_service().verify_watermark(watermark_b64, payload)
        return success_response(data=result)

    @zen_bp.get("/complexity/profile")
    @login_required
    def complexity_profile():
        profile = _get_complexity_service().get_profile(current_user.id)
        return success_response(data=profile)

    @zen_bp.post("/complexity/evolve")
    @login_required
    def complexity_evolve():
        data = request.get_json(silent=True) or {}
        new_archetype = str(data.get("archetype", "novice"))
        if new_archetype not in ("novice", "day_trader", "strategist"):
            return _validation_error("invalid archetype")
        profile = _get_complexity_service().evolve_archetype(current_user.id, new_archetype)
        return success_response(data=profile)

    @zen_bp.get("/complexity/ui-layers")
    @login_required
    def complexity_ui_layers():
        layers = _get_complexity_service().get_ui_layers(current_user.id)
        return success_response(data={"layers": layers})

    blueprint.register_blueprint(zen_bp)


@register_routes(
    name="zen_mode",
    context="system",
    description="Zen Mode: focus mode, resonance field, strategy vault, watermark, adaptive complexity",
)
def register_zen_mode_routes(bp, ctx):
    _register_zen_mode_routes(bp, ctx)
