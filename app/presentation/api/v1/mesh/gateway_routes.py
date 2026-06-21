"""Mesh gateway manifest, nodes, events and publish routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.mesh._helpers import unavailable_response
from app.presentation.api.v1.mesh.runtime import MeshRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_mesh_gateway_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: MeshRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/mesh/manifest")
    @login_required
    def mesh_manifest():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.get_manifest(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/mesh/nodes")
    @login_required
    def mesh_nodes():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.list_nodes(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/mesh/agents/discover")
    @login_required
    def mesh_discover_agents():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        role = (request.args.get("role") or "").strip() or None
        region = (request.args.get("region") or "").strip() or None
        return ok_response(
            data=svc.discover_agents(role=role, region=region),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/mesh/events/recent")
    @login_required
    def mesh_recent_events():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=30, min_value=1)
        limit = min(limit, 100)
        return ok_response(
            data=svc.list_recent(limit=limit),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/mesh/publish")
    @login_required
    def mesh_publish():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        if not body.get("event_name"):
            raise ValidationError("event_name_required")
        payload = svc.publish(body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "mesh_publish_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/mesh/health")
    @login_required
    def mesh_health():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.health(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/mesh/browsers")
    @login_required
    def mesh_browsers():
        svc = runtime.gateway_service
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.list_browser_nodes(), legacy_alias_key=None, enable_legacy_alias=legacy)
