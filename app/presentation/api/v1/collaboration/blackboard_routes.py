from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback


def register_collaboration_blackboard_routes(
    blueprint: Blueprint,
    *,
    ctx: Any,
    legacy: bool,
    uid: Callable[[], int],
    require_team_member: Callable[[int], None],
) -> None:
    @blueprint.get("/teams/<int:team_id>/blackboard")
    @login_required
    @service_fallback("team_blackboard_service")
    def team_blackboard_list(team_id: int):
        svc = getattr(ctx, "team_blackboard_service", None)
        require_team_member(team_id)
        symbol = (request.args.get("symbol") or "").strip() or None
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 200) if limit_raw else 80
        except ValueError:
            limit = 80
        payload = svc.list_notes(team_id, symbol=symbol, limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/blackboard")
    @login_required
    @service_fallback("team_blackboard_service")
    def team_blackboard_submit(team_id: int):
        svc = getattr(ctx, "team_blackboard_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        evidence_key = (body.get("evidence_key") or "").strip()
        evidence_value = (body.get("evidence_value") or "").strip()
        if not evidence_key or not evidence_value:
            raise ValidationError("evidence_key_and_value_required")
        payload = svc.submit_note(
            team_id=team_id,
            user_id=uid(),
            evidence_key=evidence_key,
            evidence_value=evidence_value,
            agent_role=(body.get("agent_role") or "member").strip(),
            symbol=(body.get("symbol") or "").strip() or None,
            strength=(body.get("strength") or "moderate").strip(),
            narrative=(body.get("narrative") or "").strip(),
            payload=body.get("payload") if isinstance(body.get("payload"), dict) else None,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/blackboard/consensus")
    @login_required
    @service_fallback("team_blackboard_service")
    def team_blackboard_consensus(team_id: int):
        svc = getattr(ctx, "team_blackboard_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or request.args.get("symbol") or "").strip() or None
        payload = svc.synthesize_consensus(team_id, symbol=symbol)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
