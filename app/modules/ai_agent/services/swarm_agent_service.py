from app.domain.dto.service_result import GenericResponseDTO

from app.core.logger import get_logger
from typing import Any
import uuid

from app.domain.ports.agent_ports import SwarmOrchestratorPort, ExpertSkillPort
from app.domain.ports import IExperimentRepository
from app.domain.entities import Experiment
from app.modules.system.services.sentinel.agent_telemetry_service import AgentTelemetryService
from app.domain.schemas.agent_schemas import SwarmRunRequest


logger = get_logger(__name__)

class SwarmAgentService:
    """Application service for multi-agent swarm operations."""

    def __init__(
        self,
        swarm_port: SwarmOrchestratorPort | None = None,
        skill_port: ExpertSkillPort | None = None,
        experiment_repo: IExperimentRepository | None = None,
        telemetry: AgentTelemetryService | None = None,
    ):
        self.swarm_port = swarm_port
        self.skill_port = skill_port
        self._experiment_repo = experiment_repo
        self._telemetry = telemetry

    @property
    def experiment_repo(self):
        if self._experiment_repo is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._experiment_repo = resolve_optional_service(IExperimentRepository)
        return self._experiment_repo

    @property
    def telemetry(self):
        if self._telemetry is None:
            self._telemetry = AgentTelemetryService()
        return self._telemetry

    def start_research_swarm(
        self,
        request: SwarmRunRequest | None = None,
        *,
        symbol: str = "",
        topic: str = "",
        preset: str = "investment_committee"
    ) -> GenericResponseDTO:
        """Start a multi-agent research swarm and register an experiment."""
        if request is None:
            request = SwarmRunRequest(symbol=symbol, topic=topic, preset=preset)
        actual_topic = request.topic or f"Comprehensive analysis of {request.symbol}"
        context = request.context or {"symbol": request.symbol}

        logger.info(f"Starting research swarm for {request.symbol} with preset {request.preset}")
        swarm_result = self.swarm_port.run_swarm(
            preset_name=request.preset,
            topic=actual_topic,
            context=context
        )

        # Create initial experiment record
        if "error" not in swarm_result:
            run_id = swarm_result.get("id", "")
            exp = Experiment(
                id=str(uuid.uuid4()),
                name=f"{request.preset}-{request.symbol}",
                swarm_run_id=run_id,
                preset_name=request.preset,
                status="running"
            )
            self.experiment_repo.save(exp)

            self.telemetry.report_event(
                event="swarm_started",
                task_id=run_id,
                task_name=f"swarm.{request.preset}",
                detail=f"Swarm run started for {request.symbol}",
                meta={"preset": request.preset, "symbol": request.symbol}
            )

        return swarm_result


    def get_skill_insights(self, skill_name: str) -> GenericResponseDTO:
        """Get financial insights from a specific expert skill."""
        return self.skill_port.load_skill(skill_name)

    def list_capabilities(self) -> GenericResponseDTO:
        """List all available swarm presets and expert skills."""
        return {
            "presets": self.swarm_port.list_presets(),
            "skills": self.skill_port.list_skills(),
        }

    def get_swarm_status(self, run_id: str) -> GenericResponseDTO | None:
        """Query the status of an ongoing or completed swarm run."""
        return self.swarm_port.get_run_status(run_id)

    def list_recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent swarm runs for dashboard."""
        runs = []
        # Get runs from experiment repository
        experiments = self.experiment_repo.list_all()[:limit]

        for exp in experiments:
            status = exp.status or "unknown"
            # Get swarm status if available
            swarm_status = None
            if exp.swarm_run_id:
                swarm_status = self.swarm_port.get_run_status(exp.swarm_run_id)

            runs.append({
                "id": exp.swarm_run_id or exp.id,
                "experiment_id": exp.id,
                "preset_name": exp.preset_name,
                "status": status,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
                "tasks": swarm_status.get("tasks", []) if swarm_status else []
            })

        return runs
