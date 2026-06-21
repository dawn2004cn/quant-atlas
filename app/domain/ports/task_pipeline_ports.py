from __future__ import annotations
"""Task pipeline and DAG visualization ports."""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TaskNode:
    """A node in the task DAG."""
    task_id: str
    task_name: str
    label: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_sec: float | None = None
    error: str | None = None
    children: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TaskPipeline:
    """A complete task pipeline DAG."""
    pipeline_id: str
    name: str
    description: str
    nodes: list[TaskNode] = field(default_factory=list)
    root_task_ids: list[str] = field(default_factory=list)


class TaskPipelinePort(ABC):
    """Port for task pipeline DAG tracking."""

    @abstractmethod
    def start_pipeline(self, name: str, description: str = "") -> str:
        """Start a new pipeline, return pipeline_id."""
        raise NotImplementedError

    @abstractmethod
    def add_node(self, pipeline_id: str, node: TaskNode) -> None:
        """Add a node to the pipeline."""
        raise NotImplementedError

    @abstractmethod
    def complete_node(self, pipeline_id: str, task_id: str, status: str, error: str | None = None) -> None:
        """Mark a node as completed."""
        raise NotImplementedError

    @abstractmethod
    def get_pipeline(self, pipeline_id: str) -> TaskPipeline | None:
        """Get pipeline by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_active_pipelines(self) -> list[TaskPipeline]:
        """List all active pipelines."""
        raise NotImplementedError


class TaskObserverPort(ABC):
    """Port for observing task events (for unified monitoring)."""

    @abstractmethod
    def on_task_queued(self, task_id: str, task_name: str, meta: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_task_started(self, task_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_task_completed(self, task_id: str, result: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_task_failed(self, task_id: str, error: str) -> None:
        raise NotImplementedError