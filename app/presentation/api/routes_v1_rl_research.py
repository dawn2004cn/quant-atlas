"""Offline RL research API — never live execution."""

from __future__ import annotations

from flask import Blueprint, request

from app.core.registry import register_routes
from app.presentation.api.responses import error_response, success_response


@register_routes(name="rl_research", context="strategy", description="Offline RL research sidecar")
def register_rl_research_routes(blueprint, ctx=None) -> None:
    _ = ctx
    bp = Blueprint("rl_research", __name__, url_prefix="/strategy/rl-research")

    @bp.get("/status")
    def rl_status():
        from app.modules.strategy.services.rl_research_service import rl_research_status

        return success_response(rl_research_status(spec_name=request.args.get("spec")))

    @bp.get("/latest")
    def rl_latest():
        from app.domain.alpha.rl_research import load_latest_policy

        spec = (request.args.get("spec") or "cn_day_v0").strip()
        policy = load_latest_policy(spec_name=spec)
        if not policy:
            return error_response("rl_policy_not_found", code=404)
        return success_response(policy)

    @bp.post("/train")
    def rl_train():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            body = {}
        from app.modules.strategy.services.rl_research_service import run_rl_research_tick

        result = run_rl_research_tick(
            spec_name=body.get("spec_name") or body.get("spec"),
            symbol=body.get("symbol"),
            episodes=body.get("episodes"),
            prefer_live_bars=bool(body.get("prefer_live_bars", True)),
        )
        return success_response(result)

    @bp.post("/infer")
    def rl_infer():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            body = {}
        from app.modules.strategy.services.rl_research_service import infer_rl_action

        try:
            ret_1 = float(body.get("ret_1") or 0.0)
            ma_bias_5 = float(body.get("ma_bias_5") or 0.0)
        except (TypeError, ValueError):
            return error_response("invalid_features", code=400)
        result = infer_rl_action(
            ret_1=ret_1,
            ma_bias_5=ma_bias_5,
            spec_name=body.get("spec_name") or body.get("spec"),
        )
        if not result.get("ok"):
            return error_response(str(result.get("error") or "infer_failed"), code=400)
        return success_response(result)

    @bp.post("/live")
    def rl_live_blocked():
        from app.modules.strategy.services.rl_research_service import RlLiveForbiddenError, refuse_live_execution

        try:
            refuse_live_execution()
        except RlLiveForbiddenError as exc:
            return error_response(str(exc), code=403)
        return error_response("rl_live_forbidden", code=403)

    blueprint.register_blueprint(bp)
