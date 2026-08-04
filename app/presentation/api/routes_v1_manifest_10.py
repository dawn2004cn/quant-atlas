"""Quant Atlas 10.0 API routes — unified manifest and resonance service."""

from __future__ import annotations

from flask import Blueprint, request

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback
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
    legacy = ctx.enable_legacy_response_fields

    @blueprint.route("/manifest/10.0", methods=["GET"])
    @service_fallback("manifest_service_10")
    def get_manifest_10():
        """Get unified 10.0 manifest — status of all new components."""
        service = ctx.manifest_service_10
        try:
            manifest = service.get_manifest()
            return ok_response(
                data=manifest,
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as exc:
            logger.error("get_manifest_10 failed: %s", exc)
            return ok_response(
                data={"ok": False, "error": str(exc)},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )

    @blueprint.route("/manifest/10.0/component/<component_name>", methods=["GET"])
    @service_fallback("manifest_service_10")
    def get_component_detail(component_name: str):
        """Get detailed status for a specific 10.0 component."""
        service = ctx.manifest_service_10
        try:
            detail = service.get_component_detail(component_name)
            return ok_response(
                data=detail,
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as exc:
            logger.error("get_component_detail failed: %s", exc)
            return ok_response(
                data={"ok": False, "error": str(exc)},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )


@register_routes(
    name="resonance",
    context="perception",
    description="Perception Resonance API (10.0)",
    depends_on=["perception_resonance_service"],
)
def register_resonance_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register perception resonance service routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.route("/perception/resonance/stats", methods=["GET"])
    @service_fallback("perception_resonance_service")
    def get_resonance_stats():
        """Get resonance service statistics."""
        service = ctx.perception_resonance_service
        try:
            stats = service.get_stats()
            return ok_response(
                data=stats,
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as exc:
            logger.error("get_resonance_stats failed: %s", exc)
            return ok_response(
                data={"ok": False, "error": str(exc)},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )

    @blueprint.route("/perception/resonance/log", methods=["GET"])
    @service_fallback("perception_resonance_service")
    def get_resonance_log():
        """Get recent resonance actions."""
        service = ctx.perception_resonance_service
        try:
            limit = int(request.args.get("limit", 100))
            log = service.get_action_log(limit=limit)
            return ok_response(
                data={"ok": True, "log": log, "count": len(log)},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as exc:
            logger.error("get_resonance_log failed: %s", exc)
            return ok_response(
                data={"ok": False, "error": str(exc)},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
