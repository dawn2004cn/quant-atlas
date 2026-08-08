"""Shadow Account SPA API — journal upload analysis."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from app.modules.ai_agent.services.shadow_account_analysis_service import (
    analyze_upload,
    get_status,
)
from .common import ok_response
from .v1_context import ApiV1Context


def _user_key() -> str:
    return str(getattr(current_user, "id", "") or getattr(current_user, "username", "") or "user")


@register_routes(name="shadow_account", context="ai_agent", description="Shadow Account journal analysis")
def register_shadow_account_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/shadow-account/status")
    @login_required
    def shadow_account_status():
        """Return the user's last shadow-account analysis snapshot."""
        data = get_status(_user_key())
        return ok_response(
            data=data or {},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/shadow-account/analyze")
    @login_required
    def shadow_account_analyze():
        """Upload a trade journal (CSV/XLSX) and return analysis metrics."""
        upload = request.files.get("file")
        try:
            result = analyze_upload(_user_key(), upload)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
