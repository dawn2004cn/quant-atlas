"""Mesh perception layer routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.mesh.runtime import MeshRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_mesh_perception_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: MeshRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/mesh/perception")
    @login_required
    def mesh_perception_manifest():
        from app.core.mesh.perception_layer import get_perception_layer

        layer = get_perception_layer()
        if layer is None:
            return ok_response(
                data={"ok": True, "enabled": False, "message": "perception_layer_disabled"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        return ok_response(
            data={"ok": True, "enabled": True, **layer.get_manifest()},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/mesh/perception/vectors")
    @login_required
    def mesh_perception_vectors():
        from app.core.mesh.perception_layer import get_perception_layer

        layer = get_perception_layer()
        if layer is None:
            return ok_response(data={"ok": True, "vectors": []}, legacy_alias_key=None, enable_legacy_alias=legacy)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1, max_value=200)
        return ok_response(
            data={"ok": True, "vectors": layer.list_vectors(limit=limit)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/mesh/perception/publish")
    @login_required
    def mesh_perception_publish():
        from app.core.mesh.perception_bridge import publish_perception

        body = request.get_json(silent=True) or {}
        result = publish_perception(
            text=body.get("text"),
            embedding=body.get("embedding"),
            metadata=body.get("metadata"),
            ttl_seconds=body.get("ttl_seconds", 300),
        )
        if not result.get("ok"):
            raise ValidationError(result.get("error") or "perception_publish_failed")
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/mesh/perception/subscribe")
    @login_required
    def mesh_perception_subscribe():
        from app.core.mesh.perception_bridge import subscribe_perception

        body = request.get_json(silent=True) or {}
        result = subscribe_perception(
            text=body.get("text"),
            embedding=body.get("embedding"),
            threshold=float(body.get("threshold", 0.7)),
            label=body.get("label", ""),
        )
        if not result.get("ok"):
            raise ValidationError(result.get("error") or "perception_subscribe_failed")
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/mesh/perception/query")
    @login_required
    def mesh_perception_query():
        from app.core.mesh.perception_layer import get_perception_layer

        layer = get_perception_layer()
        if layer is None:
            raise ValidationError("perception_layer_not_initialized")

        body = request.get_json(silent=True) or {}
        top_k = int(body.get("top_k", 5))
        min_sim = float(body.get("min_similarity", 0.5))
        results = layer.query(
            text=body.get("text"),
            embedding=body.get("embedding"),
            top_k=min(top_k, 50),
            min_similarity=min_sim,
        )
        return ok_response(
            data={"ok": True, "results": results, "count": len(results)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
