"""AI hedge fund agents, research and validation routes."""

from __future__ import annotations

from flask import Blueprint

from app.presentation.api.common import ok_response
from app.presentation.api.route_deps import build_ai_route_deps, require_swarm_service
from app.presentation.api.v1.ai_hedge_fund.runtime import AiHedgeFundRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_ai_hedge_fund_query_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: AiHedgeFundRuntime,
) -> None:
    @blueprint.route("/agents", methods=["GET"])
    def list_agents():
        """List available AI Hedge Fund agents."""
        agents = runtime.service._agent_adapter.list_agents()
        return ok_response(data={"agents": agents})

    @blueprint.route("/research/<symbol>", methods=["GET"])
    def get_research_report(symbol: str):
        """Get research report for a specific symbol."""
        report = runtime.service.get_research_report(symbol)
        return ok_response(data=report)

    @blueprint.route("/validation/<job_id>", methods=["GET"])
    def get_validation_status(job_id: str):
        """Get RD-Agent validation status."""
        require_swarm_service(build_ai_route_deps(ctx))
        return ok_response(data={"status": "pending", "job_id": job_id})
