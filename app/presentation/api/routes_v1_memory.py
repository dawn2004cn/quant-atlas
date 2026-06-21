from __future__ import annotations
"""API v1: Memory optimization routes using Apache Arrow."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import NotFoundError, ValidationError
from .common import ok_resource, ok_response
from .route_deps import MemoryRouteDeps, build_memory_route_deps
from .v1_context import ApiV1Context
from app.core.registry import register_routes


@register_routes(name="memory_optimization", context="data", description="Memory optimization routes using Apache Arrow")
def register_memory_optimization_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: MemoryRouteDeps | None = None,
) -> None:
    route_deps = deps or build_memory_route_deps(ctx)
    memory_service = route_deps.memory_optimization_service

    @blueprint.post("/memory/create-table")
    @login_required
    def memory_create_table():
        """Create an optimized Arrow table from data."""
        body = request.get_json(silent=True) or {}

        table_name = body.get("table_name", "").strip()
        data = body.get("data", [])
        pool_name = body.get("pool", "").strip() or None

        if not table_name:
            raise ValidationError("table_name_required")
        if not data:
            raise ValidationError("data_required")

        result = memory_service.create_optimized_table(table_name, data, pool_name)

        return ok_resource(
            resource=result,
            resource_key="table",
            enable_legacy_alias=False,
        )

    @blueprint.get("/memory/table")
    @login_required
    def memory_get_table():
        """Get table data as list of dicts."""
        table_name = request.args.get("table_name", "").strip()
        pool_name = request.args.get("pool", "").strip() or None

        if not table_name:
            raise ValidationError("table_name_required")

        data = memory_service.get_table(table_name, pool_name)

        if data is None:
            raise NotFoundError("table_not_found", details={"table_name": table_name})

        return ok_resource(
            resource={"table_name": table_name, "data": data},
            resource_key="table_data",
            enable_legacy_alias=False,
        )

    @blueprint.get("/memory/stats")
    @login_required
    def memory_stats():
        """Get memory statistics."""
        pool_name = request.args.get("pool", "").strip() or None

        stats = memory_service.get_memory_stats(pool_name)

        return ok_resource(
            resource=stats,
            resource_key="memory_stats",
            enable_legacy_alias=False,
        )

    @blueprint.delete("/memory/clear")
    @login_required
    def memory_clear():
        """Clear memory pool."""
        pool_name = request.args.get("pool", "").strip() or None

        memory_service.clear_pool(pool_name)

        return ok_resource(
            resource={"cleared": True, "pool": pool_name or "default"},
            resource_key="memory_clear",
            enable_legacy_alias=False,
        )

    @blueprint.get("/memory/list")
    @login_required
    def memory_list():
        """List all tables in pool."""
        pool_name = request.args.get("pool", "").strip() or None
        tables = memory_service.list_tables(pool_name)

        return ok_resource(
            resource={"tables": tables, "pool": pool_name or "default"},
            resource_key="tables",
            enable_legacy_alias=False,
        )
