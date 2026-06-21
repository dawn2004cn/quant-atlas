"""Retail assistant psychology guardian routes."""

from __future__ import annotations

import json

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_bool_param
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1_context import ApiV1Context


def _enrich_psychology_payload(ctx: ApiV1Context, payload: dict, user_id: int) -> dict:
    from app.modules.user.services.user.behavior_topology_guardian import (
        enrich_psychology_with_topology,
    )

    knowledge = getattr(ctx, "user_knowledge_service", None)
    return enrich_psychology_with_topology(
        payload,
        user_knowledge_service=knowledge,
        user_id=user_id,
    )


def register_retail_assistant_psychology_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RetailAssistantRuntime,
) -> None:
    legacy = runtime.legacy

    @blueprint.get("/retail-assistant/psychology-status")
    @login_required
    def retail_assistant_psychology_status():
        """心理卫士摘要（操盘台/自选横幅用）。"""
        from app.modules.user.services.user.psychology_guardian_service import (
            build_psychology_guardian_service,
        )

        user_id = int(getattr(current_user, "id", None) or 0)
        svc = build_psychology_guardian_service(
            signal_observation_service=getattr(ctx, "signal_observation_service", None),
            audit_trail_service=getattr(ctx, "user_audit_trail_service", None),
        )
        payload = _enrich_psychology_payload(ctx, svc.status_summary(user_id), user_id)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/retail-assistant/psychology-scan")
    @login_required
    def retail_assistant_psychology_scan():
        """当前用户心理卫士巡检（等同批量任务但仅扫描本人）。"""
        from app.modules.user.services.user.psychology_guardian_batch_service import (
            run_psychology_guardian_for_user,
        )

        user_id = int(getattr(current_user, "id", None) or 0)
        body = request.get_json(silent=True) or {}
        push = parse_bool_param(
            request.args.get("notify"),
            name="notify",
            default=bool(body.get("notify")),
        )
        payload = run_psychology_guardian_for_user(
            user_id,
            push_alerts=push,
            task_message_store=getattr(ctx, "task_message_store", None),
            lifecycle_service=getattr(ctx, "user_lifecycle_service", None),
            signal_observation_service=getattr(ctx, "signal_observation_service", None),
            audit_trail_service=getattr(ctx, "user_audit_trail_service", None),
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/retail-assistant/psychology-guardian")
    @login_required
    def retail_assistant_psychology_guardian():
        """心理卫士：检测追涨杀跌等情绪化操作模式。"""
        from app.modules.user.services.user.psychology_guardian_service import (
            build_psychology_guardian_service,
        )

        user_id = int(getattr(current_user, "id", None) or 0)
        history_raw = request.args.get("history_json")
        history = None
        if history_raw:
            try:
                history = json.loads(history_raw)
            except json.JSONDecodeError as exc:
                raise ValidationError("invalid_history_json") from exc
        svc = build_psychology_guardian_service(
            signal_observation_service=getattr(ctx, "signal_observation_service", None),
            audit_trail_service=getattr(ctx, "user_audit_trail_service", None),
        )
        payload = _enrich_psychology_payload(
            ctx,
            svc.analyze_user_behavior(user_id=user_id, operation_history=history),
            user_id,
        )
        if parse_bool_param(request.args.get("notify"), name="notify", default=False):
            pushed = svc.push_alerts_to_message_center(
                ctx.task_message_store,
                user_id=user_id,
                alerts=payload.get("alerts") or [],
                lifecycle_service=getattr(ctx, "user_lifecycle_service", None),
            )
            payload["messages_pushed"] = pushed
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
