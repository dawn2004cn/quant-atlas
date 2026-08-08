from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback


def register_collaboration_research_routes(
    blueprint: Blueprint,
    *,
    ctx: Any,
    legacy: bool,
    uid: Callable[[], int],
    require_team_member: Callable[[int], None],
) -> None:
    @blueprint.get("/teams/<int:team_id>/research-feed")
    @login_required
    @service_fallback("team_research_channel_service")
    def team_research_feed(team_id: int):
        svc = getattr(ctx, "team_research_channel_service", None)
        require_team_member(team_id)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 40
        except ValueError:
            limit = 40
        payload = svc.list_feed(team_id, limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/research-feed/publish")
    @login_required
    @service_fallback("team_research_channel_service")
    def team_research_publish(team_id: int):
        svc = getattr(ctx, "team_research_channel_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        content_text = (body.get("content_text") or body.get("content") or "").strip()
        author = getattr(current_user, "username", None) or str(uid())
        payload = svc.publish_research(
            team_id=team_id,
            user_id=uid(),
            author_name=author,
            content_text=content_text,
            provenance_id=(body.get("provenance_id") or "").strip() or None,
            symbol=(body.get("symbol") or "").strip() or None,
            attachments=body.get("attachments") if isinstance(body.get("attachments"), list) else None,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/research-feed/<int:post_id>/challenge")
    @login_required
    @service_fallback("team_research_channel_service")
    def team_research_challenge(team_id: int, post_id: int):
        svc = getattr(ctx, "team_research_channel_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        challenge_text = (body.get("challenge_text") or body.get("content") or "").strip()
        author = getattr(current_user, "username", None) or str(uid())
        payload = svc.logic_challenge(
            post_id=post_id,
            user_id=uid(),
            author_name=author,
            challenge_text=challenge_text,
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "challenge_failed")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
