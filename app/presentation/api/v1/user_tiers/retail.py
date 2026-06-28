"""User Tier API — Retail tier routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.v1.user_tiers._http import tier_success

logger = get_logger(__name__)

# Local blueprint for naming/grouping; registered under /user-tiers
_bp = Blueprint("retail", __name__)


def _get_services():
    from app.modules.user.services.retail_tier_service import (
        AiMentorService,
        CopyTradingService,
        NLToStrategyService,
        PsychologyTrackerService,
    )
    return NLToStrategyService(), AiMentorService(), CopyTradingService(), PsychologyTrackerService()


# ── NL → Strategy ──

@_bp.post("/retail/nl-to-strategy")
@login_required
def retail_nl_to_strategy():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    strategy = svc.parse(str(data.get("input", "")), current_user.id)
    payload = {
        "strategy": strategy,
        "readable": svc.to_readable(strategy),
    }
    if data.get("preview_backtest", True):
        try:
            import random

            from app.modules.strategy.services.boutique_tier_service import VectorizedBacktestService
            bt = VectorizedBacktestService()
            n = 120
            returns = [random.gauss(0.0005, 0.015) for _ in range(n)]
            signals = [1.0 if i % 20 < 10 else -1.0 for i in range(n)]
            backtest = bt.run(strategy.strategy_id, returns, signals)
            payload["backtest"] = backtest
        except Exception as exc:
            logger.debug("NL strategy backtest preview skipped: %s", exc)
    return tier_success(payload)


# ── AI Mentor ──

@_bp.post("/retail/mentor/advise")
@login_required
def retail_mentor_advise():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    advice = svc.advise(
        symbol=str(data.get("symbol", "")),
        factor_values=data.get("factors", {}),
    )
    return tier_success(advice)


# ── Copy Trading ──

@_bp.post("/retail/copy-trade/subscribe")
@login_required
def retail_copy_subscribe():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    sub = svc.subscribe(
        follower_id=current_user.id,
        provider_id=int(data.get("provider_id", 0)),
        provider_name=str(data.get("provider_name", "")),
        allocation_pct=float(data.get("allocation_pct", 10)),
    )
    return tier_success(sub)


@_bp.post("/retail/copy-trade/signal")
@login_required
def retail_copy_signal():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    signal = svc.publish_signal(
        provider_id=current_user.id,
        symbol=str(data.get("symbol", "")),
        action=str(data.get("action", "buy")),
        quantity=int(data.get("quantity", 0)),
        price=float(data.get("price", 0)),
    )
    return tier_success(signal)


@_bp.get("/retail/copy-trade/provider-rating/<int:provider_id>")
@login_required
def retail_copy_provider_rating(provider_id):
    _, _, svc, _ = _get_services()
    result = svc.get_provider_rating(provider_id)
    return tier_success(result)


@_bp.get("/retail/copy-trade/portfolio")
@login_required
def retail_copy_portfolio():
    _, _, svc, _ = _get_services()
    result = svc.get_follower_portfolio(current_user.id)
    return tier_success(result)


# ── Psychology Tracker ──

@_bp.post("/retail/psychology/record")
@login_required
def retail_psychology_record():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    event = svc.record_event(
        user_id=current_user.id,
        event_type=str(data.get("event_type", "")),
        symbol=str(data.get("symbol", "")),
        severity=float(data.get("severity", 0.5)),
    )
    return tier_success(event)


@_bp.get("/retail/psychology/report")
@login_required
def retail_psychology_report():
    _, _, _, svc = _get_services()
    report = svc.get_report(current_user.id)
    return tier_success(report)


@_bp.get("/retail/psychology/insights")
@login_required
def retail_psychology_insights():
    _, _, _, svc = _get_services()
    days = request.args.get("days", 30, type=int)
    result = svc.get_insights(current_user.id, days)
    return tier_success(result)


@_bp.get("/retail/psychology/weekly")
@login_required
def retail_psychology_weekly():
    _, _, _, svc = _get_services()
    result = svc.get_weekly_summary(current_user.id)
    return tier_success(result)


# ── Registration ──

@register_routes(name="retail", context="system", description="Retail tier: NL→Strategy, Mentor, Copy Trade, Psychology")
def register_retial_routes(blueprint, ctx) -> None:
    blueprint.register_blueprint(_bp, url_prefix="/user-tiers")
