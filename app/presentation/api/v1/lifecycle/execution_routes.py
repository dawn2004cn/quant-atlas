"""Lifecycle execution-layer routes (SOR, algos, circuit breaker)."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.lifecycle.runtime import get_execution_services
from app.presentation.api.v1_context import ApiV1Context


def register_lifecycle_execution_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @blueprint.post("/exec/sor/register-venue")
    @login_required
    def exec_sor_register():
        svc, _, _ = get_execution_services()
        data = request.get_json(silent=True) or {}
        from app.modules.execution.services.smart_execution_service import VenueProfile

        svc.register_venue(VenueProfile(**data))
        return success_response()

    @blueprint.post("/exec/sor/route")
    @login_required
    def exec_sor_route():
        svc, _, _ = get_execution_services()
        data = request.get_json(silent=True) or {}
        venues = svc.route(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "buy")),
            quantity=int(data.get("quantity", 0)),
        )
        return success_response(data={"venues": venues})

    @blueprint.post("/exec/algo/vwap")
    @login_required
    def exec_algo_vwap():
        _, svc, _ = get_execution_services()
        data = request.get_json(silent=True) or {}
        algo = svc.generate_vwap(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "buy")),
            total_quantity=int(data.get("quantity", 0)),
            volume_profile=data.get("volume_profile", [1] * 10),
            start=datetime.fromisoformat(data.get("start", datetime.now().isoformat())),
            end=datetime.fromisoformat(data.get("end", datetime.now().isoformat())),
        )
        return success_response(data=algo)

    @blueprint.post("/exec/algo/twap")
    @login_required
    def exec_algo_twap():
        _, svc, _ = get_execution_services()
        data = request.get_json(silent=True) or {}
        algo = svc.generate_twap(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "buy")),
            total_quantity=int(data.get("quantity", 0)),
            num_slices=int(data.get("slices", 10)),
            start=datetime.fromisoformat(data.get("start", datetime.now().isoformat())),
            end=datetime.fromisoformat(data.get("end", datetime.now().isoformat())),
        )
        return success_response(data=algo)

    @blueprint.post("/exec/algo/iceberg")
    @login_required
    def exec_algo_iceberg():
        _, svc, _ = get_execution_services()
        data = request.get_json(silent=True) or {}
        algo = svc.generate_iceberg(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "buy")),
            total_quantity=int(data.get("quantity", 0)),
            display_size=int(data.get("display_size", 100)),
            price=float(data.get("price", 0)),
        )
        return success_response(data=algo)

    @blueprint.post("/exec/circuit-breaker/check")
    @login_required
    def exec_circuit_breaker():
        _, _, svc = get_execution_services()
        data = request.get_json(silent=True) or {}
        check_type = str(data.get("check", "daily_loss"))
        event = None
        if check_type == "daily_loss":
            event = svc.check_daily_loss(
                current_user.id,
                float(data.get("pnl", 0)),
                float(data.get("capital", 1)),
            )
        elif check_type == "position_limit":
            event = svc.check_position_limit(
                current_user.id,
                str(data.get("symbol", "")),
                float(data.get("position_value", 0)),
                float(data.get("portfolio_value", 1)),
            )
        elif check_type == "drawdown":
            event = svc.check_drawdown(current_user.id, float(data.get("drawdown", 0)))
        if event:
            return success_response(data={"triggered": True, "event": event})
        return success_response(data={"triggered": False})
