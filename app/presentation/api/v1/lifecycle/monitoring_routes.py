"""Lifecycle monitoring-layer routes (drift, attribution, rebalance, RLHF)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.lifecycle.runtime import get_monitoring_services
from app.presentation.api.v1_context import ApiV1Context


def register_lifecycle_monitoring_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @blueprint.post("/monitor/drift/feed-live")
    @login_required
    def monitor_drift_feed_live():
        svc, _, _, _ = get_monitoring_services()
        data = request.get_json(silent=True) or {}
        svc.feed_live_signal(str(data.get("strategy_id", "")), float(data.get("value", 0)))
        return success_response()

    @blueprint.post("/monitor/drift/feed-backtest")
    @login_required
    def monitor_drift_feed_backtest():
        svc, _, _, _ = get_monitoring_services()
        data = request.get_json(silent=True) or {}
        svc.feed_backtest_signal(str(data.get("strategy_id", "")), float(data.get("value", 0)))
        return success_response()

    @blueprint.get("/monitor/drift/detect/<strategy_id>")
    @login_required
    def monitor_drift_detect(strategy_id):
        svc, _, _, _ = get_monitoring_services()
        return success_response(data=svc.detect_drift(strategy_id))

    @blueprint.post("/monitor/attribution")
    @login_required
    def monitor_attribution():
        _, svc, _, _ = get_monitoring_services()
        data = request.get_json(silent=True) or {}
        result = svc.attribute(
            strategy_id=str(data.get("strategy_id", "")),
            total_pnl=float(data.get("total_pnl", 0)),
            market_return=float(data.get("market_return", 0)),
            strategy_beta=float(data.get("beta", 1)),
            estimated_slippage=float(data.get("slippage", 0)),
            expected_alpha=float(data.get("expected_alpha", 0)),
        )
        return success_response(data=result)

    @blueprint.post("/monitor/rebalance")
    @login_required
    def monitor_rebalance():
        _, _, svc, _ = get_monitoring_services()
        data = request.get_json(silent=True) or {}
        suggestion = svc.suggest(
            strategy_id=str(data.get("strategy_id", "")),
            current_regime=str(data.get("regime", "sideways")),
            strategy_performances=data.get("performances", {}),
        )
        return success_response(data=suggestion.__dict__)

    @blueprint.post("/monitor/rlhf/feedback")
    @login_required
    def monitor_rlhf():
        _, _, _, svc = get_monitoring_services()
        data = request.get_json(silent=True) or {}
        feedback = svc.compute_reward(
            strategy_id=str(data.get("strategy_id", "")),
            pnl=float(data.get("pnl", 0)),
            sharpe=float(data.get("sharpe", 0)),
            max_drawdown=float(data.get("max_drawdown", 0)),
        )
        svc.feed_to_prompt_evolution(feedback)
        return success_response(data=feedback.__dict__)
