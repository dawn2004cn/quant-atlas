"""API v1: Arbiter consensus, review learning, and correction intents."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_response
from .v1_context import ApiV1Context
from .decorators import service_fallback


@register_routes(name="arbiter", context="system", description="Arbiter consensus and review")
def register_arbiter_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register arbiter-related routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/system/arbiter/consensus")
    @login_required
    @service_fallback("swarm_arbiter_service")
    def arbiter_consensus():
        """Synthesize debate consensus from EventBus-buffered rounds."""
        svc = getattr(ctx, "swarm_arbiter_service", None)
        symbol = (request.args.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        market = (request.args.get("market") or "CN").strip().upper()
        use_llm = (request.args.get("mode") or "").strip().lower() == "llm"
        payload = svc.consensus_only(symbol, market, use_llm=use_llm)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/arbiter/run")
    @login_required
    @service_fallback("swarm_arbiter_service")
    def arbiter_run():
        """Start swarms and return debate-weighted consensus."""
        svc = getattr(ctx, "swarm_arbiter_service", None)
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        market = (body.get("market") or "CN").strip().upper()
        swarm_ids = body.get("swarm_ids") or ["investment_committee"]
        if not isinstance(swarm_ids, list):
            raise ValidationError("swarm_ids_must_be_list")
        payload = svc.arbitrate(symbol, [str(s) for s in swarm_ids], market=market)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/arbiter/review")
    @login_required
    @service_fallback("arbiter_review_learning_service")
    def arbiter_review():
        """Record post-trade review; adjust future debate stance weights."""
        svc = getattr(ctx, "arbiter_review_learning_service", None)
        body = request.get_json(silent=True) or {}
        provenance_id = (body.get("provenance_id") or "").strip()
        symbol = (body.get("symbol") or "").strip()
        predicted = (body.get("predicted_verdict") or "").strip()
        outcome = (body.get("actual_outcome") or "").strip()
        if not provenance_id or not symbol or not predicted or not outcome:
            raise ValidationError("review_fields_required")
        market = (body.get("market") or "CN").strip().upper()
        pnl_raw = body.get("pnl_pct")
        pnl = float(pnl_raw) if pnl_raw is not None else None
        payload = svc.record_review(
            provenance_id=provenance_id,
            symbol=symbol,
            market=market,
            predicted_verdict=predicted,
            actual_outcome=outcome,
            pnl_pct=pnl,
            notes=str(body.get("notes") or ""),
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/arbiter/learning")
    @login_required
    @service_fallback("arbiter_review_learning_service")
    def arbiter_learning_state():
        """Current learned stance weights and recent reviews."""
        svc = getattr(ctx, "arbiter_review_learning_service", None)
        symbol = (request.args.get("symbol") or "").strip() or None
        return ok_response(
            data={
                "stance_weights": svc.get_stance_weights(),
                "reviews": svc.list_reviews(symbol=symbol, limit=30),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/correction-intents")
    @login_required
    @service_fallback("correction_intent_service")
    def correction_intents_pending():
        """Pending arbiter correction intent for a symbol."""
        svc = getattr(ctx, "correction_intent_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        market = (request.args.get("market") or "CN").strip().upper()
        intent = svc.get_pending(symbol, market)
        return ok_response(
            data={"intent": intent.model_dump() if intent else None},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    blueprint.register_blueprint(Blueprint("_arbiter_dummy", __name__))
