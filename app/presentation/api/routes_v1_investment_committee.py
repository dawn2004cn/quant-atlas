from __future__ import annotations
"""投资委员会 API 路由.

Replaces direct infrastructure imports with application-level service calls
from the ``ApiV1Context``.
"""

from flask import Blueprint, request
from flask_login import login_required

from ...core.registry import register_routes
from .common import ok_resource, ok_response, require_ctx_service
from .v1_context import ApiV1Context
from .decorators import require_role


@register_routes(name="investment_committee", context="ai_agent", description="投资委员会 API")
def register_investment_committee_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """注册投资委员会相关路由."""

    @blueprint.get("/ai/committee/status")
    @login_required
    def get_committee_status():
        """获取投资委员会状态."""
        market_service = require_ctx_service(ctx, "market_service")
        ic_service = ctx.investment_committee_service

        # Delegate to the application service.
        if ic_service is not None:
            return ok_resource(
                resource=ic_service.get_status(market_service=market_service),
                resource_key="committee_status",
            )

        # Fallback: if no application service is wired, return a minimal
        # response.  The actual committee logic is in infrastructure and
        # should be wired as an application service in a future phase.
        return ok_resource(
            resource={
                "data_source": "unavailable",
                "markets": {},
                "overall_regime": "unknown",
                "risk_level": "medium",
                "recommended_strategies": [],
                "strategies": [],
                "portfolio": {
                    "total_capital": 0,
                    "available_cash": 0,
                    "positions_count": 0,
                    "total_value": 0,
                    "total_pnl": 0,
                },
            },
            resource_key="committee_status",
        )

    @blueprint.get("/ai/committee/agents")
    @login_required
    def get_committee_agents():
        """获取各 Agent 意见."""
        ic_service = ctx.investment_committee_service
        if ic_service is not None:
            opinions = ic_service.get_agent_opinions()
            return ok_resource(resource={"agents": opinions}, resource_key="committee_agents")
        return ok_resource(resource={"agents": []}, resource_key="committee_agents")

    @blueprint.post("/ai/committee/run")
    @login_required
    @require_role("can_manage_users")
    def run_committee_analysis():
        """运行完整的投资委员会分析."""
        ic_service = ctx.investment_committee_service
        if ic_service is not None:
            decision = ic_service.run_analysis()
            return ok_resource(
                resource={
                    "overall_regime": decision.overall_regime,
                    "risk_level": decision.risk_level,
                    "selected_stocks": [
                        {
                            "symbol": s.symbol if hasattr(s, "symbol") else s.get("symbol", ""),
                            "name": s.name if hasattr(s, "name") else s.get("name", ""),
                            "strategy": s.strategy if hasattr(s, "strategy") else s.get("strategy", ""),
                            "entry_price": s.entry_price if hasattr(s, "entry_price") else s.get("entry_price", 0),
                            "stop_loss": s.stop_loss if hasattr(s, "stop_loss") else s.get("stop_loss", 0),
                            "take_profit": s.take_profit if hasattr(s, "take_profit") else s.get("take_profit", 0),
                            "confidence": s.confidence if hasattr(s, "confidence") else s.get("confidence", 0),
                        }
                        for s in decision.selected_stocks
                    ],
                    "trade_decisions": decision.trade_decisions,
                    "reasoning": decision.reasoning,
                },
                resource_key="committee_decision",
            )
        return ok_resource(
            resource={"selected_stocks": [], "trade_decisions": [], "reasoning": ""},
            resource_key="committee_decision",
        )

    @blueprint.get("/ai/committee/portfolio")
    @login_required
    def get_portfolio():
        """获取当前组合状态."""
        ic_service = ctx.investment_committee_service
        if ic_service is not None:
            result = ic_service.get_portfolio()
            return ok_resource(resource=result, resource_key="portfolio")
        return ok_resource(
            resource={
                "portfolio": {"total_capital": 0, "available_cash": 0, "positions": []},
                "records": [],
                "summary": {},
            },
            resource_key="portfolio",
        )

    @blueprint.get("/ai/committee/history")
    @login_required
    def get_trade_history():
        """获取交易历史."""
        ic_service = ctx.investment_committee_service
        if ic_service is not None:
            history = ic_service.get_trade_history(limit=100)
            return ok_resource(resource={"history": history}, resource_key="trade_history")
        return ok_resource(resource={"history": []}, resource_key="trade_history")
