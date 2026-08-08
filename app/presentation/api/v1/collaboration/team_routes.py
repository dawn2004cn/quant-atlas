from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback


def register_collaboration_team_routes(
    blueprint: Blueprint,
    *,
    ctx: Any,
    legacy: bool,
    uid: Callable[[], int],
) -> None:
    @blueprint.get("/collaboration/context")
    @login_required
    @service_fallback("collaboration_service")
    def collaboration_user_context():
        svc = getattr(ctx, "collaboration_service", None)
        payload = svc.get_user_context(uid())
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams")
    @login_required
    @service_fallback("collaboration_service")
    def create_team():
        svc = getattr(ctx, "collaboration_service", None)
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            raise ValidationError("team_name_required")
        payload = svc.create_team(
            user_id=uid(),
            name=name,
            slug=(body.get("slug") or "").strip() or None,
            tenant_slug=(body.get("tenant_slug") or "").strip() or None,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/members")
    @login_required
    @service_fallback("collaboration_service")
    def join_team(team_id: int):
        svc = getattr(ctx, "collaboration_service", None)
        body = request.get_json(silent=True) or {}
        role = (body.get("role") or "member").strip()
        payload = svc.join_team(user_id=uid(), team_id=team_id, role=role)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
