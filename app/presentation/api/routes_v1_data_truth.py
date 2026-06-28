from __future__ import annotations

"""Data Truth Guardian API — Quant Atlas 9.0 Step Four."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from app.domain.data_truth.guardian_schema import GuardianQuorumRequest, GuardianScanRequest

from ...application.errors import ValidationError
from .common import ok_response
from .decorators import require_role, service_fallback
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context


@register_routes(name="data_truth", context="data", description="Data Truth Guardian API (Quant Atlas 9.0 Step Four)")
def register_data_truth_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/data-truth/manifest")
    @login_required
    @service_fallback("data_truth_guardian_service")
    def data_truth_manifest():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        return ok_response(data=svc.get_manifest(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/data-truth/pending")
    @login_required
    @service_fallback("data_truth_guardian_service")
    def data_truth_pending():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        return ok_response(data=svc.list_pending(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data-truth/scan")
    @login_required
    @service_fallback("data_truth_guardian_service")
    def data_truth_scan():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols") or []
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbols:
            raise ValidationError("symbols_required")
        try:
            req = GuardianScanRequest.model_validate({**body, "symbols": symbols})
        except Exception as exc:
            raise ValidationError("invalid_scan_request", details={"reason": str(exc)}) from exc
        payload = svc.scan(req)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "scan_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data-truth/quorum")
    @login_required
    @service_fallback("data_truth_guardian_service")
    def data_truth_quorum():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols") or []
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbols:
            raise ValidationError("symbols_required")
        try:
            req = GuardianQuorumRequest.model_validate({**body, "symbols": symbols})
        except Exception as exc:
            raise ValidationError("invalid_quorum_request", details={"reason": str(exc)}) from exc
        payload = svc.quorum_scan(req)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "quorum_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data-truth/heal")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("data_truth_guardian_service")
    def data_truth_heal():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        action = str(body.get("action") or "resync_qlib").strip()
        market = str(body.get("market") or "CN").strip()
        return ok_response(
            data=svc.heal(symbol=symbol, market=market, action=action),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data-truth/heal-log")
    @login_required
    @service_fallback("data_truth_guardian_service")
    def data_truth_heal_log():
        svc = getattr(ctx, "data_truth_guardian_service", None)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=30, min_value=1)
        limit = min(limit, 100)
        return ok_response(
            data=svc.list_heal_log(limit=limit),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
