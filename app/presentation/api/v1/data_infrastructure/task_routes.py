from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, NotFoundError, ValidationError
from app.core.runtime_config import get_runtime
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import require_role

logger = logging.getLogger(__name__)


def register_data_task_routes(
    blueprint: Blueprint,
    *,
    legacy: bool,
    task_dispatcher: Any,
    task_message_store: Any,
) -> None:
    @blueprint.get("/tasks")
    @login_required
    def list_tasks():
        from app.tasks.registry import ensure_task_registry, get_tasks_by_category

        ensure_task_registry()
        tasks = get_tasks_by_category()
        return ok_response(data={"tasks": tasks}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/tasks/run")
    @login_required
    @require_role("can_manage_users")
    def run_task():
        from app.tasks.registry import ensure_task_registry, get_task_info

        ensure_task_registry()
        body = request.get_json(silent=True) or {}
        task_name = (body.get("task_name") or "").strip()
        params = body.get("params", {})
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if not task_name:
            raise ValidationError("task_name_required")

        task_info = get_task_info(task_name)
        if not task_info:
            raise NotFoundError(
                "task_not_registered",
                details={"task_name": task_name},
            )

        task_func = task_info["func"]

        if enable_celery and not sync:
            if task_func is not None and hasattr(task_func, "delay"):
                _, task_id, enqueued = task_dispatcher.dispatch(
                    task_func,
                    task_name=task_name,
                    kwargs=params,
                    bucket_seconds=300,
                )
                steps = list(task_info.get("estimated_steps") or ["排队", "执行", "持久化", "完成"])
                try:
                    from app.tasks.task_wiring import init_task_progress

                    init_task_progress(task_id, task_name=task_name, steps=steps)
                except Exception as exc:
                    logger.warning("task_routes.init_task_progress: %s", exc)
                return ok_response(
                    data={
                        "mode": "async",
                        "task_id": task_id,
                        "task_name": task_name,
                        "params": params,
                        "estimated_steps": steps,
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            raise ExternalServiceError(
                "task_not_callable_or_celery_unavailable",
                details={"task_name": task_name},
            )

        try:
            result = task_func(**params)
            return ok_response(
                data={**result, "mode": "sync", "task_name": task_name},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as exc:
            raise ValidationError(
                "task_run_failed",
                details={"task_name": task_name, "reason": str(exc)},
            ) from exc
