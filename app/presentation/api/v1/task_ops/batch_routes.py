"""Scheduled batch job trigger routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response, require_data_ingestion_role, require_research_write_role
from app.presentation.api.v1.task_ops.runtime import TaskOpsRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_task_ops_batch_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TaskOpsRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/system/retail-meta-learning-evolve")
    @login_required
    def system_retail_meta_learning_evolve():
        require_data_ingestion_role()
        from app.modules.user.services.user.meta_learning_evolve_service import run_meta_learning_evolve

        force = request.args.get("force") in ("1", "true", "yes")
        body = request.get_json(silent=True) if request.is_json else None
        if isinstance(body, dict) and body.get("force"):
            force = True
        out = run_meta_learning_evolve(
            force=bool(force),
            task_message_store=runtime.ctx.task_message_store,
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/retail-psychology-scan")
    @login_required
    def system_retail_psychology_scan():
        require_data_ingestion_role()
        from app.modules.user.services.user.psychology_guardian_batch_service import run_psychology_guardian_batch

        out = run_psychology_guardian_batch(
            push_alerts=True,
            task_message_store=runtime.ctx.task_message_store,
            lifecycle_service=getattr(runtime.ctx, "user_lifecycle_service", None),
            audit_trail_service=getattr(runtime.ctx, "user_audit_trail_service", None),
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/factor-ic-check")
    @login_required
    def system_factor_ic_check():
        if not runtime.ctx.enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")
        require_research_write_role()
        from app.tasks.factor_ic_alerts import run_factor_ic_monitor

        out = run_factor_ic_monitor()
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)
