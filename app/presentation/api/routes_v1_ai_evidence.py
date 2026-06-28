from __future__ import annotations
"""API v1：AI 可信证据链。"""


from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .decorators import service_fallback
from .common import ok_response, parse_market
from .request_parsers import parse_bool_param
from .v1_context import ApiV1Context


@register_routes(name="ai_evidence", context="ai_agent", description="AI 可信证据链")
def register_ai_evidence_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register AI evidence endpoints."""

    @blueprint.get("/ai/evidence")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_bundle():
        svc = getattr(ctx, "ai_evidence_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        include_news = parse_bool_param(
            request.args.get("include_news"),
            name="include_news",
            default=True,
        )
        user_hypothesis = (request.args.get("user_hypothesis") or "").strip() or None
        hypothesis_id = (request.args.get("hypothesis_id") or "").strip() or None
        payload = svc.build_bundle(
            symbol=symbol,
            market=parse_market(request.args.get("market", "CN")),
            include_news=include_news,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/ai/evidence/calibration")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_calibration():
        svc = getattr(ctx, "ai_evidence_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        bundle = svc.build_bundle(
            symbol=symbol,
            market=parse_market(request.args.get("market", "CN")),
            include_news=False,
        )
        return ok_response(
            data={
                "symbol": bundle["symbol"],
                "market": bundle["market"],
                "calibration": bundle["calibration"],
                "trust": bundle["trust"],
                "feedback": bundle["feedback"],
            },
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/ai/evidence/feedback")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_feedback():
        svc = getattr(ctx, "ai_evidence_service", None)
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        row = svc.record_feedback(
            symbol=symbol,
            market=parse_market(str(body.get("market") or "CN")),
            vote=str(body.get("vote") or "neutral"),
            comment=str(body.get("comment") or ""),
            source=str(body.get("source") or "ai_evidence"),
            user_id=str(getattr(current_user, "id", "") or "") or None,
        )
        return ok_response(
            data=row,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/ai/evidence/replay")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_replay():
        """Deep replay timeline for evidence graph."""
        from ...modules.ai_agent.services.evidence_replay_service import EvidenceReplayService
        evidence_svc = getattr(ctx, "ai_evidence_service", None)

        symbol = (request.args.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        market = (request.args.get("market") or "CN").strip().upper()
        minutes_raw = request.args.get("minutes_back") or request.args.get("minutes_ago") or "120"
        try:
            minutes_back = min(max(int(minutes_raw), 5), 720)
        except ValueError:
            minutes_back = 120
        svc = EvidenceReplayService(ai_evidence_service=evidence_svc)
        payload = svc.build_timeline(symbol, market=market, minutes_back=minutes_back)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.post("/ai/evidence/what-if")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_what_if():
        """Counterfactual hypothesis against replay context."""
        from ...modules.ai_agent.services.evidence_replay_service import EvidenceReplayService

        evidence_svc = getattr(ctx, "ai_evidence_service", None)
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or "").strip().upper()
        hypothesis = str(body.get("user_hypothesis") or body.get("hypothesis") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        if not hypothesis:
            raise ValidationError("user_hypothesis_required")
        market = str(body.get("market") or "CN").strip().upper()
        try:
            minutes_ago = int(body.get("minutes_ago") or 0)
        except (TypeError, ValueError):
            minutes_ago = 0
        minutes_ago = min(max(minutes_ago, 0), 720)
        svc = EvidenceReplayService(ai_evidence_service=evidence_svc)
        payload = svc.what_if(
            symbol,
            market=market,
            user_hypothesis=hypothesis,
            minutes_ago=minutes_ago,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

    @blueprint.get("/ai/evidence/hit-rate")
    @login_required
    @service_fallback("ai_evidence_service")
    def ai_evidence_hit_rate():
        """AI diagnosis hit rate for user's focus sectors (plan 2.4)."""
        svc = getattr(ctx, "ai_evidence_service", None)
        symbols_raw = (request.args.get("symbols") or request.args.get("symbol") or "").strip()
        if not symbols_raw:
            raise ValidationError("symbols_required")
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        market = parse_market(request.args.get("market", "CN"))
        results = []
        for sym in symbols:
            try:
                bundle = svc.build_bundle(symbol=sym, market=market, include_news=False)
                cal = bundle.get("calibration") or {}
                results.append({
                    "symbol": sym,
                    "prediction_samples": cal.get("prediction_samples", 0),
                    "observation_samples": cal.get("observation_samples", 0),
                    "target_hit_rate": cal.get("target_hit_rate", 0),
                    "stop_hit_rate": cal.get("stop_hit_rate", 0),
                    "avg_return_pct": cal.get("avg_observation_return_pct", 0),
                    "trust_score": (bundle.get("trust") or {}).get("score", 0),
                    "trust_level": (bundle.get("trust") or {}).get("level", "low"),
                })
            except Exception as exc:
                results.append({"symbol": sym, "error": str(exc)[:100]})
        return ok_response(data={"market": market.value, "hit_rates": results}, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

