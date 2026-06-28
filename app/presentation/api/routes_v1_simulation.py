from __future__ import annotations
"""War Room simulation API — virtual scenario stress tests (Quant Atlas 7.0)."""

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from app.domain.simulation.hyper_sim_schema import HyperSimRunRequest
from app.domain.simulation_scenario import WarRoomRunRequest
from .common import ok_response
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context
from .decorators import service_fallback


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="simulation", context="research", description="War Room simulation API (Quant Atlas 7.0)")
def register_simulation_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/simulation/war-room/scenarios")
    @login_required
    @service_fallback("simulation_gateway_service")
    def war_room_scenarios():
        svc = getattr(ctx, "simulation_gateway_service", None)
        return ok_response(data=svc.list_scenarios(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/simulation/war-room/recent")
    @login_required
    @service_fallback("simulation_gateway_service")
    def war_room_recent():
        svc = getattr(ctx, "simulation_gateway_service", None)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1)
        limit = min(limit, 50)
        payload = svc.list_recent_runs(_uid(), limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/simulation/war-room/run")
    @login_required
    @service_fallback("simulation_gateway_service")
    def war_room_run():
        svc = getattr(ctx, "simulation_gateway_service", None)
        body = request.get_json(silent=True) or {}
        try:
            req = WarRoomRunRequest.from_payload(body)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError("invalid_war_room_request", details={"reason": str(exc)}) from exc
        payload = svc.run_war_room(_uid(), req)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "war_room_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/simulation/hyper/manifest")
    @login_required
    @service_fallback("hyper_simulator_service")
    def hyper_sim_manifest():
        svc = getattr(ctx, "hyper_simulator_service", None)
        return ok_response(data=svc.get_manifest(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/simulation/hyper/recent")
    @login_required
    @service_fallback("hyper_simulator_service")
    def hyper_sim_recent():
        svc = getattr(ctx, "hyper_simulator_service", None)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1)
        limit = min(limit, 50)
        return ok_response(
            data=svc.list_recent(_uid(), limit=limit),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/simulation/hyper/run")
    @login_required
    @service_fallback("hyper_simulator_service")
    def hyper_sim_run():
        svc = getattr(ctx, "hyper_simulator_service", None)
        body = request.get_json(silent=True) or {}
        try:
            req = HyperSimRunRequest.model_validate(body)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError("invalid_hyper_sim_request", details={"reason": str(exc)}) from exc
        payload = svc.run(_uid(), req)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "hyper_sim_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
