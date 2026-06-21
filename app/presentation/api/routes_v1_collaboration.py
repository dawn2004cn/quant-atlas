from __future__ import annotations
"""Collaboration OS API — tenants, teams, tenant context."""

from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import AuthorizationError, ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response, require_ctx_service
from .v1_context import ApiV1Context
from .decorators import service_fallback, require_role


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="collaboration", context="collaboration", description="Collaboration OS API (tenants, teams)")
def register_collaboration_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    def _require_team_member(team_id: int) -> None:
        collab = getattr(ctx, "collaboration_service", None)
        if collab is None:
            return
        user_ctx = collab.get_user_context(_uid())
        team_ids = {int(t.get("id")) for t in (user_ctx.get("teams") or []) if t.get("id") is not None}
        if team_id not in team_ids:
            raise AuthorizationError("team_access_denied")

    @blueprint.get("/collaboration/context")
    @login_required
    @service_fallback("collaboration_service")
    def collaboration_user_context():
        svc = getattr(ctx, "collaboration_service", None)
        payload = svc.get_user_context(_uid())
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
            user_id=_uid(),
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
        payload = svc.join_team(user_id=_uid(), team_id=team_id, role=role)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/blackboard")
    @login_required
    @service_fallback("team_blackboard_service")
    def team_blackboard_list(team_id: int):
        svc = getattr(ctx, "team_blackboard_service", None)
        _require_team_member(team_id)
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
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        evidence_key = (body.get("evidence_key") or "").strip()
        evidence_value = (body.get("evidence_value") or "").strip()
        if not evidence_key or not evidence_value:
            raise ValidationError("evidence_key_and_value_required")
        payload = svc.submit_note(
            team_id=team_id,
            user_id=_uid(),
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
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or request.args.get("symbol") or "").strip() or None
        payload = svc.synthesize_consensus(team_id, symbol=symbol)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/research-feed")
    @login_required
    @service_fallback("team_research_channel_service")
    def team_research_feed(team_id: int):
        svc = getattr(ctx, "team_research_channel_service", None)
        _require_team_member(team_id)
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
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        content_text = (body.get("content_text") or body.get("content") or "").strip()
        author = getattr(current_user, "username", None) or str(_uid())
        payload = svc.publish_research(
            team_id=team_id,
            user_id=_uid(),
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
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        challenge_text = (body.get("challenge_text") or body.get("content") or "").strip()
        author = getattr(current_user, "username", None) or str(_uid())
        payload = svc.logic_challenge(
            post_id=post_id,
            user_id=_uid(),
            author_name=author,
            challenge_text=challenge_text,
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "challenge_failed")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/sequence-scope")
    @login_required
    @service_fallback("sequence_chain_service")
    def team_sequence_scope(team_id: int):
        """Set provenance visibility for subsequent sequence chains in this process."""
        svc = getattr(ctx, "sequence_chain_service", None)
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        visibility = (body.get("visibility") or "team").strip()
        svc.set_scope(
            visibility=visibility,
            team_id=team_id,
            owner_user_id=_uid(),
        )
        return ok_response(
            data={
                "ok": True,
                "team_id": team_id,
                "visibility": visibility,
                "owner_user_id": _uid(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/cross-team/alerts")
    @login_required
    @service_fallback("cross_team_meta_learning_service")
    def cross_team_alerts():
        """Site-wide alerts when multiple teams agree on the same symbol verdict."""
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
        """Anonymized success/failure patterns pooled across tenants."""
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
        """Re-scan recent team consensus rows and emit pending site alerts."""
        svc = getattr(ctx, "cross_team_meta_learning_service", None)
        payload = svc.scan_pending_consensus()
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

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
        _require_team_member(team_id)
        payload = svc.list_team_workflows(team_id)
        presets = svc.list_presets()
        payload["presets"] = presets.get("presets") or []
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/teams/<int:team_id>/workflows/<workflow_id>")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_detail(team_id: int, workflow_id: str):
        svc = getattr(ctx, "team_workflow_service", None)
        _require_team_member(team_id)
        payload = svc.get_team_workflow(team_id, workflow_id)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "workflow_not_found")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/workflows")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_save(team_id: int):
        svc = getattr(ctx, "team_workflow_service", None)
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        payload = svc.save_team_workflow(_uid(), team_id, body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "save_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/teams/<int:team_id>/workflows/<workflow_id>/run")
    @login_required
    @service_fallback("team_workflow_service")
    def team_workflow_run(team_id: int, workflow_id: str):
        svc = getattr(ctx, "team_workflow_service", None)
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        author = getattr(current_user, "username", None) or "Member"
        payload = svc.start_run(
            _uid(),
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
        _require_team_member(team_id)
        body = request.get_json(silent=True) or {}
        payload = svc.advance_run(
            _uid(),
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
        _require_team_member(team_id)
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
        except ValueError:
            limit = 30
        payload = svc.list_runs(team_id, limit=limit)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/meta-arbiter/synthesize")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("meta_arbiter_service")
    def meta_arbiter_synthesize():
        """Manually trigger cross-team meta-arbitration for a symbol."""
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
