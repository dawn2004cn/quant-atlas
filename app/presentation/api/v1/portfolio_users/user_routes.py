"""User administration and profile routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_collection, ok_response
from app.presentation.api.v1.portfolio_users.runtime import PortfolioUserRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_portfolio_user_admin_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None,
    *,
    runtime: PortfolioUserRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    user_service = runtime.user_service

    @blueprint.get("/users")
    @login_required
    def users():
        runtime.require_manage_users()
        users_list = user_service.list_users()
        return ok_collection(items=users_list, item_key="users", enable_legacy_alias=legacy)

    @blueprint.get("/roles")
    @login_required
    def list_roles_api():
        runtime.require_manage_users()
        roles = user_service.list_roles()
        return ok_collection(items=roles, item_key="roles", enable_legacy_alias=legacy)

    @blueprint.post("/users")
    @login_required
    def create_user():
        runtime.require_manage_users()
        payload = request.get_json(silent=True) or {}
        success, message = user_service.create_user(
            payload.get("username", "").strip(),
            payload.get("password", ""),
            payload.get("role", "viewer"),
        )
        runtime.require_ok(success, message, code="user_create_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.route("/users/<username>/role", methods=["PATCH"])
    @login_required
    def patch_user_role(username: str):
        runtime.require_manage_users()
        payload = request.get_json(silent=True) or {}
        role_code = str(payload.get("role") or "").strip()
        success, message = user_service.set_user_role(
            username,
            role_code,
            actor_role=getattr(current_user, "role", "viewer"),
        )
        runtime.require_ok(success, message, code="user_role_update_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.delete("/users/<username>")
    @login_required
    def delete_user(username: str):
        runtime.require_manage_users()
        success, message = user_service.delete_user(username, current_user.username)
        runtime.require_ok(success, message, code="user_delete_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/change-password")
    @login_required
    def change_password():
        if not runtime.pwd_change_limiter.allow(str(current_user.user_id)):
            return ok_response(data={"error": "操作过于频繁，请 60 秒后再试"}, code="rate_limited")
        payload = request.get_json(silent=True) or {}
        success, message = user_service.change_password(
            target_username=payload.get("username", ""),
            old_password=payload.get("old_password"),
            new_password=payload.get("new_password", ""),
            confirm_password=payload.get("confirm_password", ""),
            current_username=current_user.username,
            current_role=getattr(current_user, "role", "viewer"),
        )
        runtime.require_ok(success, message, code="change_password_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/profile/avatar")
    @login_required
    def profile_avatar():
        f = request.files.get("file")
        ok, msg, url = user_service.save_avatar_upload(current_user.username, f)
        if not ok:
            raise ValidationError("avatar_upload_failed", details={"reason": msg})
        return ok_response(
            data={"ok": True, "avatar_url": url},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
