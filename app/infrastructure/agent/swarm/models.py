from __future__ import annotations

"""Swarm multi-agent system — data models.

Ported from Vibe-Trading.
"""


from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """SwarmTask lifecycle status."""
    pending = "pending"
    blocked = "blocked"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunStatus(str, Enum):
    """SwarmRun lifecycle status."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class SwarmAgentSpec(BaseModel):
    """Role definition for a single agent in a Swarm."""
    id: str
    role: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    max_iterations: int = 25
    timeout_seconds: int = 300
    model_name: str | None = None
    max_retries: int = 2


class SwarmTask(BaseModel):
    """A task node in the Swarm DAG."""
    id: str
    agent_id: str
    prompt_template: str
    depends_on: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    input_from: dict[str, str] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.pending
    summary: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    worker_iterations: int = 0


class SwarmMessage(BaseModel):
    """Message passed between agents."""
    id: str
    type: str
    from_agent: str
    to: str
    content: str
    artifact_paths: list[str] = Field(default_factory=list)
    timestamp: str


class SwarmEvent(BaseModel):
    """Swarm event log entry."""
    type: str
    agent_id: str | None = None
    task_id: str | None = None
    data: dict = Field(default_factory=dict)
    timestamp: str


class SwarmRun(BaseModel):
    """Complete state of a single Swarm preset execution."""
    id: str
    preset_name: str
    status: RunStatus = RunStatus.pending
    user_vars: dict[str, str] = Field(default_factory=dict)
    agents: list[SwarmAgentSpec] = Field(default_factory=list)
    tasks: list[SwarmTask] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None
    final_report: str | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0


class WorkerResult(BaseModel):
    """Return value after worker execution completes."""
    status: str
    summary: str
    artifact_paths: list[str] = Field(default_factory=list)
    iterations: int = 0
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
