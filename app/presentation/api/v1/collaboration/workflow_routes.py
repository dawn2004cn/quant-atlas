from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback


def register_collaboration_workflow_routes(
    blueprint: Blueprint,
    *,
    ctx: Any,
    legacy: bool,
    uid: Callable[[], int],
    require_team_member: Callable[[int], None],
) -> None:
    @blueprint.post("/teams/<int:team_id>/sequence-scope")
    @login_required
    @service_fallback("sequence_chain_service")
    def team_sequence_scope(team_id: int):
        svc = getattr(ctx, "sequence_chain_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        visibility = (body.get("visibility") or "team").strip()
        svc.set_scope(
            visibility=visibility,
            team_id=team_id,
            owner_user_id=uid(),
        )
        return ok_response(
            data={
                "ok": True,
                "team_id": team_id,
                "visibility": visibility,
                "owner_user_id": uid(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/teams/workflows/presets")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_presets():
        svc = getattr(ctx, "team_workflow_service", None)
        return ok_response(data=svc.list_presets(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/workflows/blocks")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_blocks():
        svc = getattr(ctx, "team_workflow_service", None)
        return ok_response(data=svc.designer_blocks(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/workflows")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflows_list(team_id: int):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        payload = svc.list_team_workflows(team_id)
        presets = svc.list_presets()
        payload["presets"] = presets.get("presets") or []
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/workflows/<workflow_id>")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_detail(team_id: int, workflow_id: str):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        payload = svc.get_team_workflow(team_id, workflow_id)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "workflow_not_found")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/workflows")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_save(team_id: int):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        payload = svc.save_team_workflow(uid(), team_id, body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "save_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/workflows/<workflow_id>/run")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_run(team_id: int, workflow_id: str):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        author = getattr(current_user, "username", None) or "Member"
        payload = svc.start_run(
            uid(),
            team_id,
            workflow_id,
            context=body.get("context") or body,
            author_name=str(author),
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "run_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/workflow-runs/<run_id>/advance")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_advance(team_id: int, run_id: str):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        payload = svc.advance_run(
            uid(),
            team_id,
            run_id,
            action=str(body.get("action") or "complete"),
            note=str(body.get("note") or ""),
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "advance_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/workflow-runs")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_runs(team_id: int):
        svc = getattr(ctx, "team_workflow_service", None)
        require_team_member(team_id)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
        except ValueError:
            limit = 30
        payload = svc.list_runs(team_id, limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
