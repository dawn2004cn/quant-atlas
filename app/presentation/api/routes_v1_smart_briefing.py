from __future__ import annotations
"""Smart daily briefing with generative narrative layer."""

from flask import Blueprint, request, send_file
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response, parse_market
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context
from .decorators import service_fallback


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="smart_briefing", context="ai_agent", description="Smart daily briefing with generative narrative layer")
def register_smart_briefing_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/briefing/smart-daily")
    @login_required
    @service_fallback("smart_daily_briefing_service")
    def smart_daily_briefing():
        """One-click screening + personalized narrative briefing."""
        svc = getattr(ctx, "smart_daily_briefing_service", None)
        market = parse_market(request.args.get("market", "CN"))
        top_n = parse_int_param(request.args.get("top_n"), name="top_n", default=3, min_value=1)
        top_n = min(top_n, 10)
        use_narrative = request.args.get("narrative", "1") != "0"
        role = (request.args.get("role") or "").strip() or None

        profile_svc = getattr(ctx, "user_investment_profile_service", None)
        investment_profile = None
        if profile_svc is not None:
            try:
                investment_profile = profile_svc.get_profile(_uid())
            except Exception:
                investment_profile = None

        payload = svc.generate_briefing(
            market=market,
            top_n=top_n,
            user_id=_uid(),
            role=role,
            investment_profile=investment_profile if isinstance(investment_profile, dict) else None,
            use_narrative=use_narrative,
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "briefing_failed")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/briefing/causal-report")
    @login_required
    @service_fallback("narrative_synthesis_service")
    @service_fallback("smart_daily_briefing_service")
    def causal_research_report():
        narrative_svc = getattr(ctx, "narrative_synthesis_service", None)
        briefing_svc = getattr(ctx, "smart_daily_briefing_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        market = parse_market(request.args.get("market", "CN"))
        role = (request.args.get("role") or "").strip() or None

        profile_svc = getattr(ctx, "user_investment_profile_service", None)
        investment_profile = None
        if profile_svc is not None:
            try:
                investment_profile = profile_svc.get_profile(_uid())
            except Exception:
                investment_profile = None

        briefing = briefing_svc.generate_briefing(
            market=market,
            top_n=3,
            user_id=_uid(),
            use_narrative=False,
        )
        report = narrative_svc.synthesize_causal_report(
            user_id=_uid(),
            symbol=symbol or None,
            briefing=briefing if briefing.get("ok") else {},
            investment_profile=investment_profile if isinstance(investment_profile, dict) else None,
            role=role,
        )
        return ok_response(data={"ok": True, **report}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/briefing/voice-daily")
    @login_required
    @service_fallback("voice_briefing_service")
    def voice_daily_briefing():
        """Narrative briefing script + optional OpenAI TTS audio."""
        svc = getattr(ctx, "voice_briefing_service", None)
        market = parse_market(request.args.get("market", "CN"))
        top_n = parse_int_param(request.args.get("top_n"), name="top_n", default=3, min_value=1)
        top_n = min(top_n, 8)
        synthesize = request.args.get("audio", "1") != "0"
        role = (request.args.get("role") or "").strip() or None
        payload = svc.generate_daily(
            _uid(),
            market=market.value if hasattr(market, "value") else str(market),
            top_n=top_n,
            role=role,
            synthesize_audio=synthesize,
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "voice_briefing_failed")
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/briefing/voice-daily/audio/<file_id>")
    @login_required
    @service_fallback("voice_briefing_service")
    def voice_daily_audio(file_id: str):
        svc = getattr(ctx, "voice_briefing_service", None)
        path = svc.get_audio_path(file_id)
        if path is None:
            raise ValidationError("audio_not_found", details={"file_id": file_id})
        return send_file(path, mimetype="audio/mpeg", as_attachment=False)
