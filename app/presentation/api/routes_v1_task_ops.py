from __future__ import annotations

"""Task queue / Celery admin HTTP adapters (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.task_ops import (
    TaskOpsRuntime,
    register_task_ops_batch_routes,
    register_task_ops_celery_routes,
    register_task_ops_sync_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="task_ops", context="system", description="Task queue / Celery admin")
def register_task_ops_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = TaskOpsRuntime(ctx=ctx)
    register_task_ops_celery_routes(blueprint, ctx, runtime=runtime)
    register_task_ops_sync_routes(blueprint, ctx, runtime=runtime)
    register_task_ops_batch_routes(blueprint, ctx, runtime=runtime)
