from __future__ import annotations
"""API v1: Task pipeline DAG visualization routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import NotFoundError, ValidationError
from .common import ok_resource, ok_response
from .route_deps import TaskPipelineRouteDeps, build_task_pipeline_route_deps
from .v1_context import ApiV1Context
from app.core.registry import register_routes


@register_routes(name="task_pipeline", context="data", description="Task pipeline DAG visualization")
def register_task_pipeline_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: TaskPipelineRouteDeps | None = None,
) -> None:
    route_deps = deps or build_task_pipeline_route_deps(ctx)
    pipeline_service = route_deps.task_pipeline_service

    @blueprint.post("/task-pipeline/create")
    @login_required
    def task_pipeline_create():
        """Create a new task pipeline."""
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        description = body.get("description", "").strip()

        if not name:
            raise ValidationError("name_required")

        pipeline_id = pipeline_service.create_pipeline(name, description)

        return ok_resource(
            resource={"pipeline_id": pipeline_id, "name": name},
            resource_key="pipeline",
            enable_legacy_alias=False,
        )

    @blueprint.post("/task-pipeline/add-task")
    @login_required
    def task_pipeline_add_task():
        """Add a task to a pipeline."""
        body = request.get_json(silent=True) or {}

        pipeline_id = body.get("pipeline_id", "").strip()
        task_id = body.get("task_id", "").strip()
        task_name = body.get("task_name", "").strip()
        label = body.get("label", "").strip()
        depends_on = body.get("depends_on", [])

        if not pipeline_id or not task_id or not task_name:
            raise ValidationError(
                "pipeline_task_fields_required",
                details={"required": ["pipeline_id", "task_id", "task_name"]},
            )

        pipeline_service.add_task(pipeline_id, task_id, task_name, label, depends_on)

        return ok_resource(
            resource={"added": True, "task_id": task_id},
            resource_key="task",
            enable_legacy_alias=False,
        )

    @blueprint.post("/task-pipeline/start-task")
    @login_required
    def task_pipeline_start_task():
        """Mark a task as started."""
        body = request.get_json(silent=True) or {}

        pipeline_id = body.get("pipeline_id", "").strip()
        task_id = body.get("task_id", "").strip()

        if not pipeline_id or not task_id:
            raise ValidationError(
                "pipeline_task_ids_required",
                details={"required": ["pipeline_id", "task_id"]},
            )

        pipeline_service.start_task(pipeline_id, task_id)

        return ok_resource(
            resource={"started": True, "task_id": task_id},
            resource_key="task",
            enable_legacy_alias=False,
        )

    @blueprint.post("/task-pipeline/complete-task")
    @login_required
    def task_pipeline_complete_task():
        """Mark a task as completed or failed."""
        body = request.get_json(silent=True) or {}

        pipeline_id = body.get("pipeline_id", "").strip()
        task_id = body.get("task_id", "").strip()
        error = body.get("error")

        if not pipeline_id or not task_id:
            raise ValidationError(
                "pipeline_task_ids_required",
                details={"required": ["pipeline_id", "task_id"]},
            )

        pipeline_service.complete_task(pipeline_id, task_id, error)

        return ok_resource(
            resource={"completed": True, "task_id": task_id, "error": error},
            resource_key="task",
            enable_legacy_alias=False,
        )

    @blueprint.get("/task-pipeline/list")
    @login_required
    def task_pipeline_list():
        """List all pipelines."""
        pipelines = pipeline_service.list_pipelines()

        return ok_resource(
            resource={"pipelines": pipelines},
            resource_key="pipelines",
            enable_legacy_alias=False,
        )

    @blueprint.get("/task-pipeline/<pipeline_id>")
    @login_required
    def task_pipeline_get(pipeline_id: str):
        """Get pipeline details."""
        pipeline = pipeline_service.get_pipeline(pipeline_id)

        if not pipeline:
            raise NotFoundError("pipeline_not_found", details={"pipeline_id": pipeline_id})

        return ok_resource(
            resource=pipeline,
            resource_key="pipeline",
            enable_legacy_alias=False,
        )

    @blueprint.get("/task-pipeline/<pipeline_id>/dag")
    @login_required
    def task_pipeline_dag(pipeline_id: str):
        """Get DAG visualization data."""
        dag = pipeline_service.get_dag_json(pipeline_id)

        return ok_resource(
            resource=dag,
            resource_key="dag",
            enable_legacy_alias=False,
        )
