from __future__ import annotations

"""Collaboration OS API — tenants, teams, tenant context."""

from flask import Blueprint

from app.core.middleware.request_context import require_authenticated_user_id
from app.core.registry import register_routes
from app.presentation.api.v1.collaboration._access import make_require_team_member
from app.presentation.api.v1.collaboration.blackboard_routes import register_collaboration_blackboard_routes
from app.presentation.api.v1.collaboration.research_routes import register_collaboration_research_routes
from app.presentation.api.v1.collaboration.system_meta_routes import register_collaboration_system_meta_routes
from app.presentation.api.v1.collaboration.team_routes import register_collaboration_team_routes
from app.presentation.api.v1.collaboration.workflow_routes import register_collaboration_workflow_routes
from app.presentation.api.v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="collaboration", context="collaboration", description="Collaboration OS API (tenants, teams)")
def register_collaboration_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    require_team_member = make_require_team_member(ctx, _uid)

    register_collaboration_team_routes(
        blueprint,
        ctx=ctx,
        legacy=legacy,
        uid=_uid,
    )
    register_collaboration_blackboard_routes(
        blueprint,
        ctx=ctx,
        legacy=legacy,
        uid=_uid,
        require_team_member=require_team_member,
    )
    register_collaboration_research_routes(
        blueprint,
        ctx=ctx,
        legacy=legacy,
        uid=_uid,
        require_team_member=require_team_member,
    )
    register_collaboration_workflow_routes(
        blueprint,
        ctx=ctx,
        legacy=legacy,
        uid=_uid,
        require_team_member=require_team_member,
    )
    register_collaboration_system_meta_routes(
        blueprint,
        ctx=ctx,
        legacy=legacy,
    )
