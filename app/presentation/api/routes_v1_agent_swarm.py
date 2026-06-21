from __future__ import annotations

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError

from app.application.errors import ExternalServiceError, NotFoundError, ValidationError
from app.core.registry import register_routes
from app.core.tracing.tracer import set_trace_id
from app.domain.schemas.agent_schemas import SwarmRunRequest

from .common import ok_response
from .route_deps import AiRouteDeps, build_ai_route_deps, require_swarm_service
from .v1_context import ApiV1Context


@register_routes(name="agent_swarm", context="research", description="Agent swarm routes")
def register_agent_swarm_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: AiRouteDeps | None = None,
) -> None:
    route_deps = deps or build_ai_route_deps(ctx)

    agent_swarm_bp = Blueprint("agent-swarm", __name__, url_prefix="/agent-swarm")

    @agent_swarm_bp.before_request
    def start_trace():
        set_trace_id(request.headers.get("X-Trace-ID"))

    @agent_swarm_bp.route("/capabilities", methods=["GET"])
    def list_capabilities():
        """List all swarm presets and expert skills."""
        swarm_service = require_swarm_service(route_deps)
        # swarm_service may be RDAgentRunService which lacks list_capabilities
        if not hasattr(swarm_service, "list_capabilities"):
            return ok_response(data={"presets": [], "skills": []})
        return ok_response(data=swarm_service.list_capabilities())

    @agent_swarm_bp.route("/swarm/run", methods=["POST"])
    def run_swarm():
        """Start a multi-agent swarm run."""
        swarm_service = require_swarm_service(route_deps)
        body = request.get_json(silent=True) or {}
        try:
            req = SwarmRunRequest.model_validate(body)
        except PydanticValidationError as exc:
            raise ValidationError(
                "invalid_swarm_run_request",
                details={"errors": exc.errors()},
            ) from exc

        try:
            result = swarm_service.start_research_swarm(req)
        except TypeError as exc:
            if "takes 2 positional arguments but" in str(exc):
                raise ExternalServiceError(
                    "swarm_service_not_configured",
                    details={"reason": str(exc)},
                ) from exc
            raise
        if isinstance(result, dict) and result.get("error"):
            raise ExternalServiceError(
                "swarm_run_failed",
                details={"reason": str(result["error"])},
            )

        return ok_response(data=result)

    @agent_swarm_bp.route("/swarm/status/<run_id>", methods=["GET"])
    def get_swarm_status(run_id: str):
        """Get status of a swarm run."""
        swarm_service = require_swarm_service(route_deps)
        status = swarm_service.get_swarm_status(run_id)
        if status is None:
            raise NotFoundError("swarm_run_not_found", details={"run_id": run_id})
        return ok_response(data=status)

    @agent_swarm_bp.route("/experiments", methods=["GET"])
    def list_experiments():
        """List all completed or ongoing experiments."""
        swarm_service = require_swarm_service(route_deps)
        experiments = swarm_service.experiment_repo.list_all()
        data = [{"created_at": exp.created_at.isoformat(), **{k: v for k, v in exp.__dict__.items() if not k.startswith('_')}} for exp in experiments]
        return ok_response(data=data)

    blueprint.add_url_rule("/experiments", "list_experiments_legacy", list_experiments, methods=["GET"])

    @agent_swarm_bp.route("/experiments/<experiment_id>", methods=["GET"])
    def get_experiment(experiment_id: str):
        """Get detailed info for a specific experiment."""
        swarm_service = require_swarm_service(route_deps)
        exp = swarm_service.experiment_repo.get(experiment_id)
        if not exp:
            raise NotFoundError(
                "experiment_not_found",
                details={"experiment_id": experiment_id},
            )
        data = {"created_at": exp.created_at.isoformat(), **{k: v for k, v in exp.__dict__.items() if not k.startswith('_')}}
        return ok_response(data=data)

    blueprint.add_url_rule(
        "/experiments/<experiment_id>",
        "get_experiment_legacy",
        get_experiment,
        methods=["GET"],
    )

    @agent_swarm_bp.route("/runs", methods=["GET"])
    def list_runs():
        """List all swarm runs."""
        try:
            swarm_service = require_swarm_service(route_deps)
            # Use the application service's list_runs method (which may
            # delegate to SwarmOrchestratorAdapter internally).
            runs = swarm_service.list_all_runs(limit=50)
            return ok_response(data={"runs": runs})
        except (ValidationError, NotFoundError, ExternalServiceError):
            raise
        except Exception as exc:
            raise ExternalServiceError(
                "swarm_runs_list_failed",
                details={"reason": str(exc)},
            ) from exc

    blueprint.register_blueprint(agent_swarm_bp)
