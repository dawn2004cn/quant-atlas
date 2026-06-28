from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.ports.agent_ports import SwarmOrchestratorPort
from app.infrastructure.agent.swarm.presets import list_presets as vibe_list_presets
from app.infrastructure.agent.swarm.runtime import SwarmRuntime
from app.infrastructure.agent.swarm.store import SwarmStore

logger = get_logger(__name__)

class SwarmOrchestratorAdapter(SwarmOrchestratorPort):
    """Adapter for multi-agent swarm orchestration.

    This adapter uses the internal app.infrastructure.agent components.
    """

    def __init__(self, storage_dir: str | Path | None = None):
        try:
            # Initialize storage and runtime
            if storage_dir is None:
                # Default to project instance directory
                storage_dir = Path("instance/agents/swarms/runs")

            self.storage_path = Path(storage_dir)
            self.storage_path.mkdir(parents=True, exist_ok=True)

            self.store = SwarmStore(self.storage_path)
            self.runtime = SwarmRuntime(self.store)

            logger.info(f"SwarmOrchestratorAdapter initialized with storage at {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize swarm components: {e}")
            self.runtime = None


    def run_swarm(
        self,
        preset_name: str,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a swarm preset with a given topic."""
        if self.runtime is None:
            return {"error": "Vibe runtime not initialized"}

        user_vars = {"topic": topic}
        if context:
            for k, v in context.items():
                user_vars[k] = str(v)

        try:
            run = self.runtime.start_run(preset_name, user_vars)
            return run.model_dump()
        except Exception as e:
            logger.error(f"Error starting swarm run {preset_name}: {e}")
            return {"error": str(e)}

    def list_presets(self) -> list[str]:
        """List available swarm presets."""
        try:
            presets = vibe_list_presets()
            return [p["name"] for p in presets]
        except Exception as e:
            logger.error(f"Error listing swarm presets: {e}")
            return []

    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        """Get the status of a specific swarm run."""
        if self.store is None:
            return None

        run = self.store.load_run(run_id)
        return run.model_dump() if run else None

    def list_all_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        """List all swarm runs."""
        if self.store is None:
            return []
        try:
            runs = []
            for f in sorted(self.storage_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                try:
                    run = self.store.load_run(f.stem)
                    if run:
                        runs.append(run.model_dump())
                except Exception as e:
                    logger.warning("swarm_orchestrator_adapter.py.list_all_runs: %s", e)
            return runs
        except Exception as e:
            logger.error(f"Error listing runs: {e}")
            return []
