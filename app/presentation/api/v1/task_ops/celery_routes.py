"""Celery task monitoring and control routes."""

from __future__ import annotations

from flask import Blueprint, Response, request, stream_with_context
from flask_login import current_user, login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response, require_data_ingestion_role
from app.presentation.api.request_parsers import parse_bool_param, parse_int_param
from app.presentation.api.v1.task_ops.runtime import TaskOpsRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_task_ops_celery_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TaskOpsRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/system/active-jobs")
    @login_required
    def system_active_jobs():
        from app.modules.system.services.system.active_job_tracker_service import ActiveJobTrackerService

        if runtime.ctx.task_message_store is None:
            return ok_response(
                data={"items": [], "count": 0, "message_backend": "none"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
                count=0,
            )
        lim = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1, max_value=50)
        user_id = getattr(current_user, "id", None) if current_user.is_authenticated else None
        tracker = runtime.ctx.active_job_tracker_service or ActiveJobTrackerService(
            task_message_store=runtime.ctx.task_message_store,
        )
        payload = tracker.list_active_jobs(user_id=user_id, limit=lim)
        payload["message_backend"] = runtime.ctx.task_message_store.enabled_backend
        payload["celery_enabled"] = runtime.ctx.enable_celery
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=payload.get("count", 0),
        )

    @blueprint.get("/system/task-messages")
    @login_required
    def system_task_messages():
        if runtime.ctx.task_message_store is None:
            return ok_response(
                data={"items": [], "message_backend": "none", "celery_enabled": False},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
                count=0,
            )
        lim = parse_int_param(request.args.get("limit"), name="limit", default=80, min_value=1)
        lim = min(lim, 200)
        since_ts = (request.args.get("since_ts") or "").strip()
        items = runtime.ctx.task_message_store.list_recent(limit=lim if not since_ts else 200)
        if since_ts:
            items = [m for m in items if str(m.get("ts") or "") > since_ts]
        category = (request.args.get("category") or "").strip().lower()
        event_filter = (request.args.get("event") or "").strip().lower()
        if category == "retail_psychology":
            items = [
                m
                for m in items
                if (m.get("meta") or {}).get("category") == "retail_psychology"
                or "psychology" in str(m.get("event") or "").lower()
                or str(m.get("task_name") or "") == "retail.psychology_guardian"
            ]
        elif event_filter:
            items = [m for m in items if event_filter in str(m.get("event") or "").lower()]
        items = items[:lim]
        return ok_response(
            data={
                "items": items,
                "message_backend": runtime.ctx.task_message_store.enabled_backend,
                "celery_enabled": runtime.ctx.enable_celery,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(items),
        )

    @blueprint.get("/system/task-queue-hint")
    @login_required
    def system_task_queue_hint():
        may_ingest = getattr(current_user, "may_trigger_server_data_ingestion", lambda: False)()
        may_admin = getattr(current_user, "can_manage_users", lambda: False)()
        return ok_response(
            data={
                "celery_enabled": runtime.ctx.enable_celery,
                "message_backend": runtime.ctx.task_message_store.enabled_backend,
                "can_revoke_celery_tasks": bool(may_ingest),
                "can_terminate_celery_tasks": bool(may_admin),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/celery/inspect")
    @login_required
    def system_celery_inspect():
        from app.modules.system.services.helpers.task_ops_access import inspect_celery_snapshot

        if not runtime.ctx.enable_celery:
            raise ExternalServiceError("celery_disabled")
        snap = inspect_celery_snapshot(timeout=2.5)
        return ok_response(data=snap, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/celery/task/<task_id>")
    @login_required
    def system_celery_task_get(task_id: str):
        from app.modules.system.services.helpers.task_ops_access import get_celery_task_status

        return ok_response(data=get_celery_task_status(task_id), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/tasks/<task_id>/feedback")
    @login_required
    def system_task_feedback(task_id: str):
        from app.modules.system.services.system.task_feedback_service import TaskFeedbackService

        task_name = (request.args.get("task_name") or "").strip() or None
        steps_raw = (request.args.get("steps") or "").strip()
        estimated_steps = [s.strip() for s in steps_raw.split("|") if s.strip()] if steps_raw else None
        payload = TaskFeedbackService().build_feedback(
            task_id,
            task_name=task_name,
            estimated_steps=estimated_steps,
        )
        return ok_response(data=payload, ready=payload.get("ready"))

    @blueprint.get("/system/task-phase-plan")
    @login_required
    def system_task_phase_plan():
        from app.modules.system.services.system.task_phase_plan_service import TaskPhasePlanService

        task_name = (request.args.get("task_name") or "").strip() or None
        steps_raw = (request.args.get("steps") or "").strip()
        estimated_steps = [s.strip() for s in steps_raw.split("|") if s.strip()] if steps_raw else None
        payload = TaskPhasePlanService().build_progress(
            task_name=task_name,
            estimated_steps=estimated_steps,
            state="PENDING",
        )
        return ok_response(
            data={"task_name": task_name, **payload},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/tasks/<task_id>/stream")
    @login_required
    def system_task_stream(task_id: str):
        from app.modules.system.services.system.task_stream_service import TaskStreamService

        task_name = (request.args.get("task_name") or "").strip() or None
        steps_raw = (request.args.get("steps") or "").strip()
        estimated_steps = [s.strip() for s in steps_raw.split("|") if s.strip()] if steps_raw else None
        svc = TaskStreamService()

        def generate():
            yield from svc.iter_sse(
                task_id,
                task_name=task_name,
                estimated_steps=estimated_steps,
            )

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @blueprint.post("/system/celery/task/<task_id>/revoke")
    @login_required
    def system_celery_task_revoke(task_id: str):
        require_data_ingestion_role()
        body = request.get_json(silent=True) or {}
        terminate = parse_bool_param(body.get("terminate"), name="terminate", default=False)
        if terminate and not current_user.can_manage_users():
            raise ValidationError("terminate=true 仅管理员可执行（强制终止 Worker 子进程）")
        from app.modules.system.services.helpers.task_ops_access import revoke_celery_task

        out = revoke_celery_task(task_id, terminate=terminate)
        if out.get("ok") and runtime.ctx.task_message_store is not None:
            runtime.ctx.task_message_store.push(
                event="task_revoked",
                task_id=(task_id or "").strip(),
                task_name="inline.celery_revoke",
                detail=("已撤销" + ("（强制终止）" if terminate else ""))[:500],
                meta={"terminate": terminate},
            )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)
