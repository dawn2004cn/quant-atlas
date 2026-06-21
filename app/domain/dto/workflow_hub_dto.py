from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowHubSectionDTO(BaseModel):
    id: str
    label: str
    entrypoints: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowHubDTO(BaseModel):
    schema_version: str = "v1"
    active_jobs: list[dict[str, Any]] = Field(default_factory=list)
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    sections: list[WorkflowHubSectionDTO] = Field(default_factory=list)
    human_intervention_count: int = 0

