from __future__ import annotations
"""Borderless execution API — Quant Atlas 9.0 Step Two."""

from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_response
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context
from .decorators import service_fallback


@register_routes(name="execution", context="execution", description="Borderless execution API (9.0)")
def register_execution_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/execution/manifest")
    @login_required
    @service_fallback("borderless_execution_service")
    def execution_manifest():
        svc = getattr(ctx, "borderless_execution_service", None)
        return ok_response(data=svc.get_manifest(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/execution/qmt-status")
    @login_required
    def execution_qmt_status():
        """QMT gateway mode (simulation vs live) for ops dashboards."""
        from app.config import get_settings
        from app.infrastructure.execution.qmt_executor import qmt_executor_status

        qmt = get_settings().qmt
        return ok_response(
            data=qmt_executor_status(
                account_id=qmt.account_id or "",
                qmt_path=qmt.qmt_path or "",
            ),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/execution/route")
    @login_required
    @service_fallback("borderless_execution_service")
    def execution_route_preview():
        svc = getattr(ctx, "borderless_execution_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        market = (request.args.get("market") or "").strip() or None
        return ok_response(
            data=svc.preview_route(symbol, market=market),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/execution/orders")
    @login_required
    @service_fallback("borderless_execution_service")
    def execution_submit_order():
        svc = getattr(ctx, "borderless_execution_service", None)
        body = request.get_json(silent=True) or {}
        if not str(body.get("symbol") or "").strip():
            raise ValidationError("symbol_required")
        body.setdefault("user_id", getattr(current_user, "id", None))
        payload = svc.submit_order(body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "execution_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/execution/orders/<order_id>")
    @login_required
    @service_fallback("borderless_execution_service")
    def execution_order_status(order_id: str):
        svc = getattr(ctx, "borderless_execution_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        return ok_response(
            data=svc.get_order_status(order_id, symbol=symbol),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/execution/orders")
    @login_required
    @service_fallback("borderless_execution_service")
    def execution_recent_orders():
        svc = getattr(ctx, "borderless_execution_service", None)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1)
        limit = min(limit, 100)
        return ok_response(
            data=svc.list_recent_orders(limit=limit),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
