from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskFeedbackStepDTO(BaseModel):
    id: str
    label: str
    status: str = "pending"


class TaskFeedbackDTO(BaseModel):
    task_id: str
    task_name: str | None = None
    state: str = "PENDING"
    ready: bool = False
    successful: bool = False
    failed: bool = False
    percent: float = 0.0
    message: str = ""
    steps: list[TaskFeedbackStepDTO] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    result: Any = None
    done: bool = False
