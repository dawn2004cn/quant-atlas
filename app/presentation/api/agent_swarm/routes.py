from __future__ import annotations

"""Swarm Visualization & Management API."""


from pathlib import Path

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import NotFoundError, ValidationError
from app.domain.schemas.agent_schemas import SwarmRunRequest
from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService

from ..common import ok_response
from ..decorators import require_role


def create_agent_swarm_blueprint(
    *,
    swarm_service: SwarmAgentService,
) -> Blueprint:
    bp = Blueprint("agent_swarm_api", __name__, url_prefix="/api/agent/swarm")

    @bp.get("/runs")
    @login_required
    def list_runs():
        """Get list of swarm runs with status."""
        from app.infrastructure.agent.swarm.store import SwarmStore

        store = SwarmStore(Path("instance/agents/swarms/runs"))
        runs = store.list_runs()
        return ok_response(data=[r.model_dump() for r in runs])

    @bp.get("/run/<run_id>/dag")
    @login_required
    def get_run_dag(run_id: str):
        """Get the DAG structure and status for a specific swarm run."""
        from app.infrastructure.agent.swarm.store import SwarmStore

        store = SwarmStore(Path("instance/agents/swarms/runs"))
        run = store.load_run(run_id)
        if not run:
            raise NotFoundError("swarm_run_not_found", details={"run_id": run_id})

        # Build a graph view for the frontend
        nodes = [{"id": t.id, "agent": t.agent_id, "status": t.status, "summary": t.summary} for t in run.tasks]
        edges = [{"source": dep, "target": t.id} for t in run.tasks for dep in t.depends_on]

        return ok_response(data={"run_id": run_id, "nodes": nodes, "edges": edges})

    @bp.post("/run")
    @login_required
    @require_role("can_manage_users")
    def run_swarm():
        try:
            req = SwarmRunRequest(**request.get_json(silent=True) or {})
        except Exception as exc:
            raise ValidationError(
                "invalid_swarm_request",
                details={"reason": str(exc)},
            ) from exc

        result = swarm_service.start_research_swarm(req)
        return ok_response(data=result)

    return bp
