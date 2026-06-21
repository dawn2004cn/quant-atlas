from __future__ import annotations
"""Task pipeline DAG infrastructure implementation."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...domain.ports.task_pipeline_ports import (
    TaskNode,
    TaskPipeline,
    TaskPipelinePort,
    TaskObserverPort,
)


class InMemoryTaskPipeline(TaskPipelinePort):
    """In-memory implementation of task pipeline tracking."""

    def __init__(self):
        self._pipelines: dict[str, TaskPipeline] = {}
        self._node_status: dict[str, dict[str, Any]] = {}

    def start_pipeline(self, name: str, description: str = "") -> str:
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pipeline = TaskPipeline(
            pipeline_id=pipeline_id,
            name=name,
            description=description,
            nodes=[],
            root_task_ids=[],
        )
        self._pipelines[pipeline_id] = pipeline
        return pipeline_id

    def add_node(self, pipeline_id: str, node: TaskNode) -> None:
        if pipeline_id not in self._pipelines:
            return

        pipeline = self._pipelines[pipeline_id]
        pipeline.nodes.append(node)

        if not node.children:
            pipeline.root_task_ids.append(node.task_id)

        self._node_status[f"{pipeline_id}:{node.task_id}"] = {
            "status": node.status,
            "started_at": node.started_at,
            "completed_at": node.completed_at,
        }

    def complete_node(self, pipeline_id: str, task_id: str, status: str, error: str | None = None) -> None:
        key = f"{pipeline_id}:{task_id}"
        if key in self._node_status:
            self._node_status[key]["status"] = status
            self._node_status[key]["completed_at"] = datetime.now().isoformat()
            if error:
                self._node_status[key]["error"] = error

        for pipeline in self._pipelines.values():
            for node in pipeline.nodes:
                if node.task_id == task_id:
                    from dataclasses import replace
                    completed_node = replace(
                        node,
                        status=status,
                        completed_at=datetime.now().isoformat(),
                        error=error,
                    )
                    pipeline.nodes.remove(node)
                    pipeline.nodes.append(completed_node)
                    break

    def get_pipeline(self, pipeline_id: str) -> TaskPipeline | None:
        return self._pipelines.get(pipeline_id)

    def list_active_pipelines(self) -> list[TaskPipeline]:
        return list(self._pipelines.values())


class TaskObserverAdapter(TaskObserverPort):
    """Adapter to observe Celery task events."""

    def __init__(self, pipeline_tracker: TaskPipelinePort | None = None):
        self._tracker = pipeline_tracker or InMemoryTaskPipeline()
        self._current_pipeline_id: str | None = None

    def set_pipeline(self, pipeline_id: str) -> None:
        self._current_pipeline_id = pipeline_id

    def on_task_queued(self, task_id: str, task_name: str, meta: dict[str, Any]) -> None:
        if self._current_pipeline_id:
            node = TaskNode(
                task_id=task_id,
                task_name=task_name,
                label=task_name,
                status="queued",
            )
            self._tracker.add_node(self._current_pipeline_id, node)

    def on_task_started(self, task_id: str) -> None:
        if self._current_pipeline_id:
            self._tracker.complete_node(self._current_pipeline_id, task_id, "started")

    def on_task_completed(self, task_id: str, result: Any) -> None:
        if self._current_pipeline_id:
            self._tracker.complete_node(self._current_pipeline_id, task_id, "completed")

    def on_task_failed(self, task_id: str, error: str) -> None:
        if self._current_pipeline_id:
            self._tracker.complete_node(self._current_pipeline_id, task_id, "failed", error)

    def get_tracker(self) -> TaskPipelinePort:
        return self._tracker