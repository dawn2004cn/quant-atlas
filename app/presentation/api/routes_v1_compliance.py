"""Compliance manifest and retail disclaimers (Phase D)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.domain.compliance.retail_manifest import build_compliance_manifest
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="compliance", context="system", description="Retail compliance manifest")
def register_compliance_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/compliance/manifest")
    def compliance_manifest():
        """Public compliance copy + beta SLA targets for UI footers.

        Intentionally unauthenticated — listed in ``PUBLIC_API_V1_GET_PATHS``.
        """
        return ok_response(
            data=build_compliance_manifest(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
