from __future__ import annotations
"""Diagnosis report API routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from .common import ok_response, parse_market
from .request_parsers import parse_float_param
from .v1_context import ApiV1Context
from app.core.registry import register_routes
from .decorators import service_fallback


@register_routes(name="diagnosis", context="misc", description="Diagnosis report API routes")
def register_diagnosis_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/diagnosis/report")
    @login_required
    @service_fallback("diagnosis_report_service")
    def diagnosis_report():
        svc = getattr(ctx, "diagnosis_report_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        payload = svc.build_report(
            symbol=symbol,
            market=parse_market(request.args.get("market", "CN")),
            account_equity=parse_float_param(
                request.args.get("account_equity"),
                name="account_equity",
                default=100000.0,
                min_value=1000.0,
            ),
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/diagnosis/stock")
    @login_required
    @service_fallback("diagnosis_report_service")
    def diagnosis_stock():
        svc = getattr(ctx, "diagnosis_report_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        market = parse_market(request.args.get("market", "CN"))
        if hasattr(svc, "get_stock_diagnosis"):
            payload = svc.get_stock_diagnosis(symbol, market)
        else:
            payload = {"symbol": symbol, "market": market.value, "status": "available", "data": {}}
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
