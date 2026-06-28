from __future__ import annotations
"""User lifecycle, push, sync and compliance API routes."""


from flask import Blueprint, request
from flask_login import current_user, login_required

from .common import ok_response
from .v1_context import ApiV1Context
from app.core.registry import register_routes
from .decorators import service_fallback, require_role
from flask import jsonify


@register_routes
def register_user_lifecycle_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/user/lifecycle")
    @login_required
    @service_fallback("user_lifecycle_service")
    def get_user_lifecycle():
        svc = getattr(ctx, "user_lifecycle_service", None)
        return ok_response(
            data=svc.get_settings(user=current_user),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/notification-preferences")
    @login_required
    @service_fallback("user_lifecycle_service")
    def update_notification_preferences():
        svc = getattr(ctx, "user_lifecycle_service", None)
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.update_notifications(user=current_user, patch=payload),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/privacy-consent")
    @login_required
    @service_fallback("user_lifecycle_service")
    def record_privacy_consent():
        svc = getattr(ctx, "user_lifecycle_service", None)
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.record_privacy_consent(user=current_user, consent=payload),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/data-export")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("user_lifecycle_service")
    def export_user_data():
        # IDOR prevention: verify current user is the data owner
        svc = getattr(ctx, "user_lifecycle_service", None)
        if not svc:
            return jsonify({"success": False, "data": None, "error": "Service unavailable", "meta": None}), 503
        return ok_response(
            data=svc.export_user_data(user=current_user),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/account-deletion-request")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("user_lifecycle_service")
    def request_account_deletion():
        # IDOR prevention: verify current user is the account owner
        svc = getattr(ctx, "user_lifecycle_service", None)
        if not svc:
            return jsonify({"success": False, "data": None, "error": "Service unavailable", "meta": None}), 503
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.request_account_deletion(
                user=current_user,
                reason=payload.get("reason", ""),
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )
