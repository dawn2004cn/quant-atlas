from __future__ import annotations
"""AI committee stock selection API routes."""


import uuid

from flask import Blueprint, request
from flask_login import login_required

from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response, require_ctx_service
from .decorators import require_role
from .request_parsers import parse_float_param, parse_int_param
from .v1_context import ApiV1Context


@register_routes(name="ai_committee_selection", context="ai_agent", description="AI committee stock selection")
def register_ai_committee_selection_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register AI committee stock selection routes."""

    def _service():
        return require_ctx_service(ctx, "ai_committee_selection_service")

    @blueprint.get("/ai-committee-selection/config")
    @login_required
    def ai_committee_selection_config():
        return ok_response(data=_service().get_config(), legacy_alias_key=None)

    def _uid() -> int:
        return require_authenticated_user_id()

    @blueprint.get("/ai-committee-selection/status")
    @login_required
    def ai_committee_selection_status():
        return ok_response(data=_service().get_status(user_id=_uid()), legacy_alias_key=None)

    @blueprint.post("/ai-committee-selection/run")
    @login_required
    @require_role("can_manage_users")
    def ai_committee_selection_run():
        body = request.get_json(silent=True) or {}
        capital = parse_float_param(body.get("capital"), name="capital", default=500000, min_value=10000)
        min_positions = min(5, parse_int_param(body.get("min_positions"), name="min_positions", default=3, min_value=1))
        max_positions = min(5, parse_int_param(body.get("max_positions"), name="max_positions", default=5, min_value=min_positions))
        payload = _service().run_selection(
            user_id=_uid(),
            capital=capital,
            min_positions=min_positions,
            max_positions=max_positions,
        )
        if ctx.task_message_store is not None:
            ctx.task_message_store.push(
                event="ai_committee_selection_completed",
                task_id=f"sync-{uuid.uuid4().hex[:12]}",
                task_name="inline.ai_committee_selection",
                detail=f"AI 投委会选股完成，选出 {len(payload.get('selected_stocks') or [])} 只短线标的",
                meta={"run_id": payload.get("id"), "regime": payload.get("overall_regime")},
            )
        return ok_response(data=payload, legacy_alias_key=None)

    @blueprint.post("/ai-committee-selection/track")
    @login_required
    def ai_committee_selection_track():
        return ok_response(data=_service().track_positions(user_id=_uid()), legacy_alias_key=None)
