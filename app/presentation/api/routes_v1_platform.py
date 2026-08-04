"""Platform metadata for SPA and external clients."""

from __future__ import annotations

from flask import Blueprint

from app.core.nav_menu import api_nav_flags
from app.core.registry import register_routes
from app.core.strategic_sunset import jinja_feature_flags
from app.presentation.api.responses import success_response

blueprint = Blueprint("platform", __name__)


@register_routes(name="platform", context="system", description="Platform feature flags")
def register_platform_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx

    @blueprint.get("/platform/strategic-features")
    def strategic_features():
        """Public strategic sunset flags (no auth — drives SPA nav gating)."""
        return success_response(data={**jinja_feature_flags(), **api_nav_flags()})

    @blueprint.get("/platform/nav-menu")
    def nav_menu_flags():
        """Navigation visibility flags for SPA (no auth)."""
        return success_response(data=api_nav_flags())
