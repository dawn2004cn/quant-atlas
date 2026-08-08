from __future__ import annotations

from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import require_role, service_fallback


def register_collaboration_system_meta_routes(
    blueprint: Blueprint,
    *,
    ctx: Any,
    legacy: bool,
) -> None:
    @blueprint.get("/system/cross-team/alerts")
    @login_required
    @service_fallback("cross_team_meta_learning_service")
    def cross_team_alerts():
        svc = getattr(ctx, "cross_team_meta_learning_service", None)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
        except ValueError:
            limit = 30
        payload = svc.list_site_alerts(limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/cross-team/patterns")
    @login_required
    @service_fallback("cross_team_meta_learning_service")
    def cross_team_patterns():
        svc = getattr(ctx, "cross_team_meta_learning_service", None)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 40
        except ValueError:
            limit = 40
        payload = svc.list_anonymous_patterns(limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/cross-team/scan")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("cross_team_meta_learning_service")
    def cross_team_scan():
        svc = getattr(ctx, "cross_team_meta_learning_service", None)
        payload = svc.scan_pending_consensus()
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/meta-arbiter/synthesize")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("meta_arbiter_service")
    def meta_arbiter_synthesize():
        svc = getattr(ctx, "meta_arbiter_service", None)
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or request.args.get("symbol") or "").strip()
        market = (body.get("market") or request.args.get("market") or "CN").strip().upper()
        verdict_hint = (body.get("verdict") or request.args.get("verdict") or "").strip() or None
        use_llm = str(body.get("use_llm") or request.args.get("use_llm") or "0") == "1"
        if not symbol:
            raise ValidationError("symbol_required")
        payload = svc.synthesize(symbol, market, verdict_hint=verdict_hint, use_llm=use_llm)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "meta_arbitration_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/meta-arbiter/recent")
    @login_required
    @service_fallback("meta_arbiter_service")
    def meta_arbiter_recent():
        svc = getattr(ctx, "meta_arbiter_service", None)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
        except ValueError:
            limit = 30
        payload = svc.list_recent(limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/meta-arbiter/symbol/<symbol>")
    @login_required
    @service_fallback("meta_arbiter_service")
    def meta_arbiter_for_symbol(symbol: str):
        svc = getattr(ctx, "meta_arbiter_service", None)
        market = (request.args.get("market") or "CN").strip().upper()
        payload = svc.get_for_symbol(symbol, market)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "not_found", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
