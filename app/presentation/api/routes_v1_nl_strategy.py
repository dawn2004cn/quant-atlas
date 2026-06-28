"""NL Strategy Generator API — NL-to-Strategy with preview and history."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.core.logger import get_logger
from app.core.registry import register_routes

from .common import ok_response

logger = get_logger(__name__)


@register_routes(name="nl_strategy", context="user", description="NL-to-Strategy: parse, preview, history")
def register_nl_strategy_routes(blueprint: Blueprint, ctx) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.post("/nl-strategy/parse")
    @login_required
    def nl_strategy_parse():
        """Parse natural language into a structured strategy."""
        data = request.get_json(silent=True) or {}
        nl_input = str(data.get("input", "")).strip()
        if not nl_input:
            return ok_response(
                data={"ok": False, "error": "请输入自然语言策略描述"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        from app.modules.user.services.retail_tier_service import NLToStrategyService
        svc = NLToStrategyService()
        strategy = svc.parse(nl_input, user_id=int(getattr(current_user, "id", 0)))
        return ok_response(
            data={
                "ok": True,
                "strategy": {
                    "strategy_id": strategy.strategy_id,
                    "nl_input": strategy.nl_input,
                    "conditions": strategy.conditions,
                    "actions": strategy.actions,
                    "risk_rules": strategy.risk_rules,
                    "logic_steps": strategy.logic_steps,
                    "preview_metrics": strategy.preview_metrics,
                    "created_at": strategy.created_at,
                },
                "readable": svc.to_readable(strategy),
                "flowchart": svc.to_flowchart_json(strategy),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/nl-strategy/preview")
    @login_required
    def nl_strategy_preview():
        """Parse natural language and run a backtest preview."""
        data = request.get_json(silent=True) or {}
        nl_input = str(data.get("input", "")).strip()
        symbol = str(data.get("symbol", "000300")).strip()
        market = str(data.get("market", "CN")).strip()
        if not nl_input:
            return ok_response(
                data={"ok": False, "error": "请输入自然语言策略描述"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        from app.modules.user.services.retail_tier_service import NLToStrategyService
        svc = NLToStrategyService()
        result = svc.parse_with_preview(nl_input, symbol=symbol, market=market, user_id=int(getattr(current_user, "id", 0)))
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/nl-strategy/history")
    @login_required
    def nl_strategy_history():
        """Get user's NL strategy history."""
        from app.modules.user.services.retail_tier_service import NLToStrategyService
        svc = NLToStrategyService()
        strategies = svc.load_history(user_id=int(getattr(current_user, "id", 0)))
        return ok_response(
            data={
                "strategies": [
                    {
                        "strategy_id": s.strategy_id,
                        "nl_input": s.nl_input,
                        "conditions": s.conditions,
                        "actions": s.actions,
                        "risk_rules": s.risk_rules,
                        "preview_metrics": s.preview_metrics,
                        "created_at": s.created_at,
                    }
                    for s in strategies
                ],
                "total": len(strategies),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
