"""Dual-path routing and trade pipeline routes."""

from __future__ import annotations

import uuid

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.core.dual_path_router import PathPriority, PathTask, PathType
from app.presentation.api.responses import success_response
from app.presentation.api.v1.optimization.runtime import get_dual_path_router
from app.presentation.api.v1_context import ApiV1Context


def register_optimization_dual_path_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/dual-path/metrics")
    @login_required
    def dual_path_metrics():
        router = get_dual_path_router()
        return success_response(data=router.get_metrics())

    @blueprint.post("/dual-path/route")
    @login_required
    def dual_path_route():
        data = request.get_json(silent=True) or {}
        path_str = str(data.get("path", "fast")).lower()
        path = PathType.FAST if path_str == "fast" else PathType.SLOW
        priority_str = str(data.get("priority", "normal")).upper()
        priority = getattr(PathPriority, priority_str, PathPriority.NORMAL)

        task = PathTask(
            task_id=f"task.{uuid.uuid4().hex[:8]}",
            path=path,
            priority=priority,
            handler=str(data.get("handler", "")),
            payload=data.get("payload", {}),
            max_latency_ms=data.get("max_latency_ms", 100),
        )

        router = get_dual_path_router()
        if path == PathType.FAST:
            result = router.route_fast(task)
        else:
            result = router.route_slow(task)

        return success_response(data={"task_id": task.task_id, **result})

    @blueprint.post("/trade/pipeline")
    @login_required
    def optimization_trade_pipeline():
        """Phase II unified trade pipeline via Dual Path."""
        data = request.get_json(silent=True) or {}
        task = PathTask(
            task_id=f"pipe.{uuid.uuid4().hex[:8]}",
            path=PathType.FAST,
            priority=PathPriority.CRITICAL,
            handler="trade_pipeline_execute",
            payload={
                "user_id": current_user.id,
                **data,
            },
            max_latency_ms=200,
        )
        router = get_dual_path_router()
        routed = router.route_fast(task)
        inner = routed.get("result") if isinstance(routed.get("result"), dict) else {}
        return success_response(
            data=inner,
            meta={
                "pipeline_ok": inner.get("ok", routed.get("ok", False)),
                "latency_ms": routed.get("latency_ms"),
            },
        )
