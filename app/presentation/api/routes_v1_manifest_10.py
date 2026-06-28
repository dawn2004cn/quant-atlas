"""Quant Atlas 10.0 API routes — unified manifest and resonance service."""

from __future__ import annotations

from flask import Blueprint, request

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


@register_routes(
    name="manifest_10",
    context="system",
    description="Quant Atlas 10.0 unified manifest API",
    depends_on=["manifest_service_10"],
)
def register_manifest_10_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register 10.0 manifest routes."""

    @blueprint.route("/manifest/10.0", methods=["GET"])
    def get_manifest_10():
        """Get unified 10.0 manifest — status of all new components."""
        service = ctx.manifest_service_10
        if service is None:
            return ok_response({"ok": False, "error": "service_not_available"}), 503

        try:
            manifest = service.get_manifest()
            return ok_response(manifest)
        except Exception as exc:
            logger.error("get_manifest_10 failed: %s", exc)
            return ok_response({"ok": False, "error": str(exc)}), 500

    @blueprint.route("/manifest/10.0/component/<component_name>", methods=["GET"])
    def get_component_detail(component_name: str):
        """Get detailed status for a specific 10.0 component."""
        service = ctx.manifest_service_10
        if service is None:
            return ok_response({"ok": False, "error": "service_not_available"}), 503

        try:
            detail = service.get_component_detail(component_name)
            return ok_response(detail)
        except Exception as exc:
            logger.error("get_component_detail failed: %s", exc)
            return ok_response({"ok": False, "error": str(exc)}), 500


@register_routes(
    name="resonance",
    context="perception",
    description="Perception Resonance API (10.0)",
    depends_on=["perception_resonance_service"],
)
def register_resonance_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register perception resonance service routes."""

    @blueprint.route("/perception/resonance/stats", methods=["GET"])
    def get_resonance_stats():
        """Get resonance service statistics."""
        service = ctx.perception_resonance_service
        if service is None:
            return ok_response({"ok": False, "error": "service_not_available"}), 503

        try:
            stats = service.get_stats()
            return ok_response(stats)
        except Exception as exc:
            logger.error("get_resonance_stats failed: %s", exc)
            return ok_response({"ok": False, "error": str(exc)}), 500

    @blueprint.route("/perception/resonance/log", methods=["GET"])
    def get_resonance_log():
        """Get recent resonance actions."""
        service = ctx.perception_resonance_service
        if service is None:
            return ok_response({"ok": False, "error": "service_not_available"}), 503

        try:
            limit = int(request.args.get("limit", 100))
            log = service.get_action_log(limit=limit)
            return ok_response({"ok": True, "log": log, "count": len(log)})
        except Exception as exc:
            logger.error("get_resonance_log failed: %s", exc)
            return ok_response({"ok": False, "error": str(exc)}), 500
