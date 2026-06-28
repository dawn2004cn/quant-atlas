"""Chart Vision API — multimodal visual intelligence endpoints (10.0)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_response
from .decorators import service_fallback
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context


@register_routes(name="chart_vision", context="vision", description="Chart Vision API (10.0)")
def register_chart_vision_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/vision/analyze/<symbol>")
    @login_required
    @service_fallback("chart_vision_agent_service")
    def vision_analyze(symbol: str):
        """Full visual analysis: render chart → vision LLM → pattern detection."""
        svc = getattr(ctx, "chart_vision_agent_service", None)
        market = (request.args.get("market") or "CN").strip().upper()
        days = parse_int_param(request.args.get("days"), name="days", default=120, min_value=20, max_value=500)
        include_image = request.args.get("image", "0") == "1"

        result = svc.analyze(
            symbol=symbol,
            market=market,
            days=days,
            include_image=include_image,
        )
        if result.get("status") != "success":
            raise ValidationError(
                result.get("message") or "vision_analysis_failed",
                details={"symbol": symbol},
            )
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/vision/patterns/<symbol>")
    @login_required
    @service_fallback("chart_vision_agent_service")
    def vision_patterns(symbol: str):
        """Pattern detection only (faster, no image in response)."""
        svc = getattr(ctx, "chart_vision_agent_service", None)
        market = (request.args.get("market") or "CN").strip().upper()
        days = parse_int_param(request.args.get("days"), name="days", default=120, min_value=20, max_value=500)

        result = svc.analyze(symbol=symbol, market=market, days=days, include_image=False)
        if result.get("status") != "success":
            raise ValidationError(
                result.get("message") or "pattern_detection_failed",
                details={"symbol": symbol},
            )
        return ok_response(
            data={
                "symbol": symbol,
                "merged_signal": result.get("merged_signal"),
                "visual_analysis": result.get("visual_analysis"),
                "numerical_analysis": result.get("numerical_analysis"),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
