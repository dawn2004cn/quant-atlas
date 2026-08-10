"""Platform metadata for SPA and external clients."""

from __future__ import annotations

import time
from typing import Any

from flask import Blueprint, jsonify

from app.core.nav_menu import api_nav_flags
from app.core.registry import register_routes
from app.core.strategic_sunset import jinja_feature_flags
from app.presentation.api.responses import serialize

blueprint = Blueprint("platform", __name__)

_FEATURES_CACHE: dict[str, Any] | None = None
_FEATURES_CACHE_AT: float = 0.0
_FEATURES_TTL_SECONDS = 600.0


def _strategic_features_payload() -> dict[str, Any]:
    global _FEATURES_CACHE, _FEATURES_CACHE_AT
    now = time.time()
    if _FEATURES_CACHE is not None and (now - _FEATURES_CACHE_AT) < _FEATURES_TTL_SECONDS:
        return dict(_FEATURES_CACHE)
    payload = {**jinja_feature_flags(), **api_nav_flags()}
    _FEATURES_CACHE = dict(payload)
    _FEATURES_CACHE_AT = now
    return payload


@register_routes(name="platform", context="system", description="Platform feature flags")
def register_platform_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx

    @blueprint.get("/platform/strategic-features")
    def strategic_features():
        """Public strategic sunset flags (no auth — drives SPA nav gating)."""
        resp = jsonify(
            {
                "success": True,
                "ok": True,
                "status": "success",
                "data": serialize(_strategic_features_payload()),
                "error": None,
                "meta": {"cache_ttl": int(_FEATURES_TTL_SECONDS)},
            }
        )
        resp.headers["Cache-Control"] = "private, max-age=600"
        return resp

    @blueprint.get("/platform/nav-menu")
    def nav_menu_flags():
        """Navigation visibility flags for SPA (no auth)."""
        from app.presentation.api.responses import success_response

        return success_response(data=api_nav_flags())
