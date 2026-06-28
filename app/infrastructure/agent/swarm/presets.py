from __future__ import annotations

"""Swarm YAML preset loader.

Ported from Vibe-Trading.
"""


import uuid
from datetime import datetime, timezone
from pathlib import Path

# Presets are now in the config directory
from app.infrastructure.agent.repositories.preset_repository import PresetRepository
from app.infrastructure.agent.swarm.models import RunStatus, SwarmAgentSpec, SwarmRun, SwarmTask, TaskStatus

PRESET_REPO = PresetRepository(Path("instance/agents/swarms/presets"))

def load_preset(name: str) -> dict:
    """Load a preset from the repository."""
    data = PRESET_REPO.get_preset(name)
    if data is None:
        raise FileNotFoundError(f"Preset '{name}' not found in repository.")
    return data

def list_presets() -> list[dict]:
    """Return summary info for all available presets."""
    results: list[dict] = []
    for name in PRESET_REPO.list_presets():
        data = PRESET_REPO.get_preset(name)
        if data:
            results.append({
                "name": data.get("name", name),
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "agent_count": len(data.get("agents", [])),
                "variables": data.get("variables", []),
            })
    return results



def build_run_from_preset(preset_name: str, user_vars: dict[str, str]) -> SwarmRun:
    """Create a SwarmRun from a preset with user variables applied."""
    data = load_preset(preset_name)

    # Parse agents
    agents: list[SwarmAgentSpec] = []
    for agent_data in data.get("agents", []):
        agents.append(SwarmAgentSpec(
            id=agent_data["id"],
            role=agent_data.get("role", ""),
            system_prompt=agent_data.get("system_prompt", ""),
            tools=agent_data.get("tools", []),
            skills=agent_data.get("skills", []),
            max_iterations=agent_data.get("max_iterations", 25),
            timeout_seconds=agent_data.get("timeout_seconds", 300),
            model_name=agent_data.get("model_name"),
            max_retries=agent_data.get("max_retries", 2),
        ))

    # Parse tasks, initialize blocked_by from depends_on
    tasks: list[SwarmTask] = []
    for task_data in data.get("tasks", []):
        depends_on = task_data.get("depends_on", [])
        status = TaskStatus.blocked if depends_on else TaskStatus.pending
        tasks.append(SwarmTask(
            id=task_data["id"],
            agent_id=task_data["agent_id"],
            prompt_template=task_data.get("prompt_template", ""),
            depends_on=depends_on,
            blocked_by=list(depends_on),
            input_from=task_data.get("input_from", {}),
            status=status,
        ))

    # Generate run ID
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    run_id = f"swarm-{ts}-{short_uuid}"

    return SwarmRun(
        id=run_id,
        preset_name=preset_name,
        status=RunStatus.pending,
        user_vars=user_vars,
        agents=agents,
        tasks=tasks,
        created_at=now.isoformat(),
    )
