from __future__ import annotations
"""User context API routes."""

from flask import Blueprint
from flask_login import login_required

from app.core.registry import register_routes
from .common import ok_response
from .v1_context import ApiV1Context


def register_user_context_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/user/context/dashboard")
    @login_required
    def user_context_dashboard():
        engine = getattr(ctx, "user_context_engine", None)
        if engine is None:
            return ok_response(
                data={"error": "user_context_unavailable"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        from flask_login import current_user
        layout = engine.get_dashboard_layout(current_user.id)
        return ok_response(
            data={
                "layout_id": layout.layout_id,
                "user_id": layout.user_id,
                "cards": layout.cards,
                "updated_at": layout.updated_at,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/user/context/quick-actions")
    @login_required
    def user_context_quick_actions():
        engine = getattr(ctx, "user_context_engine", None)
        if engine is None:
            return ok_response(
                data={"items": []},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        from flask_login import current_user
        actions = engine.get_quick_actions(current_user.id)
        return ok_response(
            data={
                "items": [
                    {
                        "id": a.id,
                        "label": a.label,
                        "journey": a.journey,
                        "route": a.route,
                        "params": a.params,
                        "priority": a.priority,
                    }
                    for a in actions
                ]
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/user/context/suggestions")
    @login_required
    def user_context_suggestions():
        engine = getattr(ctx, "user_context_engine", None)
        if engine is None:
            return ok_response(
                data={"items": []},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        from flask_login import current_user
        hints = engine.get_journey_suggestions(current_user.id)
        return ok_response(
            data={
                "items": [
                    {
                        "journey": h.journey,
                        "label": h.label,
                        "reason": h.reason,
                        "target_route": h.target_route,
                        "params": h.params,
                    }
                    for h in hints
                ]
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
