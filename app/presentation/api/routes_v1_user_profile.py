from __future__ import annotations
"""User investment profile API routes."""


from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_response, ensure_service
from .v1_context import ApiV1Context
from ...core.middleware.request_context import require_authenticated_user_id


def _uid() -> int:
    return require_authenticated_user_id()



@register_routes(name="user_profile", context="user", description="User investment profile API routes")
def register_user_profile_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/user/access-policy")
    @login_required
    def get_access_policy():
        svc = ensure_service(ctx, "user_access_policy_service")
        return ok_response(
            data=svc.snapshot_for_user(current_user),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/investment-profile")
    @login_required
    def get_investment_profile():
        svc = ensure_service(ctx, "user_investment_profile_service")
        return ok_response(
            data=svc.get_profile(getattr(current_user, "id", "anonymous")),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/archetype-dna")
    @login_required
    def get_archetype_dna():
        svc = getattr(ctx, "archetype_clusterer_service", None)
        if svc is None:
            from app.modules.user.services.user.archetype_clusterer import ArchetypeClusterer

            svc = ArchetypeClusterer()
        user_id = getattr(current_user, "id", "anonymous")
        return ok_response(
            data=svc.build_dna_profile(
                user_id=user_id,
                symbol=request.args.get("symbol", "").strip(),
                sector=request.args.get("sector", "").strip(),
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/archetype")
    @login_required
    def get_archetype_mapping():
        svc = getattr(ctx, "archetype_clusterer_service", None)
        if svc is None:
            from app.modules.user.services.user.archetype_clusterer import ArchetypeClusterer

            svc = ArchetypeClusterer()
        user_id = getattr(current_user, "id", "anonymous")
        return ok_response(
            data=svc.map_user_to_archetype(
                user_id=user_id,
                symbol=request.args.get("symbol", "").strip(),
                sector=request.args.get("sector", "").strip(),
                action=request.args.get("action", "").strip(),
                stance=request.args.get("stance", "").strip(),
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/page-preferences")
    @login_required
    def get_page_preferences():
        svc = ensure_service(ctx, "page_preference_service")
        return ok_response(
            data=svc.get_preferences(getattr(current_user, "id", "anonymous")),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/decision-context")
    @login_required
    def get_decision_context():
        svc = getattr(ctx, "user_decision_context_service", None)
        if svc is None or isinstance(svc, type):
            from app.modules.system.services.ui.user_decision_context_service import (
                UserDecisionContextService,
            )

            svc = UserDecisionContextService()

        user_id = getattr(current_user, "id", "anonymous")
        profile = {}
        preferences = {}
        if ctx.user_investment_profile_service is not None:
            profile = ctx.user_investment_profile_service.get_profile(user_id)
        if ctx.page_preference_service is not None:
            preferences = ctx.page_preference_service.get_preferences(user_id)

        return ok_response(
            data=svc.build_context(
                user_id=user_id,
                role=request.args.get("role"),
                investment_profile=profile,
                page_preferences=preferences,
                page=request.args.get("page"),
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/page-preferences")
    @login_required
    def update_page_preferences():
        svc = ensure_service(ctx, "page_preference_service")
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.update_preferences(
                getattr(current_user, "id", "anonymous"),
                payload,
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/audit-trail")
    @login_required
    def list_audit_trail():
        svc = ensure_service(ctx, "user_audit_trail_service")
        limit_raw = request.args.get("limit") or "50"
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 50
        return ok_response(
            data=svc.list_user_actions(
                user_id=getattr(current_user, "id", "anonymous"),
                limit=limit,
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/audit-trail")
    @login_required
    def record_audit_trail():
        svc = ensure_service(ctx, "user_audit_trail_service")
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.record(
                user_id=getattr(current_user, "id", "anonymous"),
                action=payload.get("action", "unknown"),
                target_type=payload.get("target_type", ""),
                target_id=payload.get("target_id", ""),
                metadata=payload.get("metadata") or {},
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/investment-profile")
    @login_required
    def update_investment_profile():
        svc = ensure_service(ctx, "user_investment_profile_service")
        payload = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.update_profile(
                getattr(current_user, "id", "anonymous"),
                payload,
            ),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/user/decision-events")
    @login_required
    def record_decision_event():
        svc = getattr(ctx, "user_decision_context_service", None)
        if svc is None:
            from app.modules.system.services.ui.user_decision_context_service import (
                UserDecisionContextService,
            )
            svc = UserDecisionContextService()
        body = request.get_json(silent=True) or {}
        entry = svc.record_event(
            user_id=getattr(current_user, "id", "anonymous"),
            event_type=str(body.get("event_type", "custom")),
            symbol=str(body.get("symbol", "")),
            market=str(body.get("market", "CN")),
            page=str(body.get("page", "")),
            component=str(body.get("component", "")),
            action=str(body.get("action", "")),
            detail=body.get("detail") if isinstance(body.get("detail"), dict) else {},
        )
        return ok_response(data=entry, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.get("/user/decision-events")
    @login_required
    def list_decision_events():
        svc = getattr(ctx, "user_decision_context_service", None)
        if svc is None:
            from app.modules.system.services.ui.user_decision_context_service import (
                UserDecisionContextService,
            )
            svc = UserDecisionContextService()
        from .request_parsers import parse_int_param
        limit = parse_int_param(request.args.get("limit"), name="limit", default=30)
        event_type = request.args.get("event_type") or None
        symbol = request.args.get("symbol") or None
        rows = svc.event_history(
            getattr(current_user, "id", "anonymous"),
            limit=limit,
            event_type=event_type,
            symbol=symbol,
        )
        return ok_response(data=rows, count=len(rows), legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.get("/user/decision-events/summary")
    @login_required
    def decision_events_summary():
        svc = getattr(ctx, "user_decision_context_service", None)
        if svc is None:
            from app.modules.system.services.ui.user_decision_context_service import (
                UserDecisionContextService,
            )
            svc = UserDecisionContextService()
        return ok_response(
            data=svc.event_summary(getattr(current_user, "id", "anonymous")),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/user/persona")
    @login_required
    def get_user_persona():
        """Get user persona tier and feature mask (plan 1.3)."""
        from ...domain.services.persona_service import get_persona_service
        svc = get_persona_service()
        persona = svc.get_or_assess_default(user_id=_uid())
        return ok_response(data={
            "tier": persona.tier.value,
            "risk_tolerance": persona.risk_tolerance,
            "experience_score": persona.experience_score,
            "trading_frequency": persona.trading_frequency,
            "feature_mask": persona.features,
            "assessed_at": persona.assessed_at,
        }, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.post("/user/persona")
    @login_required
    def update_user_persona():
        """Update user persona assessment."""
        from ...domain.services.persona_service import get_persona_service
        svc = get_persona_service()
        body = request.get_json(silent=True) or {}
        rt = body.get("risk_tolerance")
        es = body.get("experience_score")
        tf = body.get("trading_frequency")
        persona = svc.assess_persona(
            user_id=_uid(),
            risk_tolerance=float(rt) if rt is not None else None,
            experience_score=float(es) if es is not None else None,
            trading_frequency=str(tf) if tf else None,
        )
        return ok_response(data={
            "tier": persona.tier.value,
            "risk_tolerance": persona.risk_tolerance,
            "experience_score": persona.experience_score,
            "trading_frequency": persona.trading_frequency,
            "feature_mask": persona.features,
            "assessed_at": persona.assessed_at,
        }, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.post("/user/persona/features")
    @login_required
    def update_persona_features():
        """Override specific UI features."""
        from ...domain.services.persona_service import get_persona_service
        svc = get_persona_service()
        body = request.get_json(silent=True) or {}
        overrides = body.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ValidationError("overrides_must_be_dict")
        updated = svc.update_features(user_id=_uid(), overrides={k: bool(v) for k, v in overrides.items()})
        if not updated:
            raise ValidationError("persona_not_found")
        return ok_response(data={
            "feature_mask": updated.features,
        }, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

