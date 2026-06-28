from __future__ import annotations

"""Task pipeline application service for DAG visualization."""


from app.core.base_service import BaseApplicationService
from app.core.registry import register_service
from app.domain.dto.pipeline_dto import (
    DagEdgeDTO,
    DagGraphDTO,
    DagNodeDTO,
    PipelineDTO,
    PipelineSummaryDTO,
    TaskNodeDTO,
)
from app.domain.ports.task_pipeline_ports import TaskNode, TaskPipeline, TaskPipelinePort
from app.modules.system.services.helpers.task_pipeline_access import (
    create_default_task_pipeline,
    create_task_observer,
)


@register_service(name="task_pipeline_service")
class TaskPipelineService(BaseApplicationService):
    """Application service for task pipeline DAG visualization."""

    def __init__(self, pipeline_port: TaskPipelinePort | None = None):
        super().__init__()
        self._tracker = pipeline_port or create_default_task_pipeline()
        self._observer = create_task_observer(self._tracker)

    def create_pipeline(self, name: str, description: str = "") -> str:
        return self._tracker.start_pipeline(name, description)

    def add_task(
        self,
        pipeline_id: str,
        task_id: str,
        task_name: str,
        label: str | None = None,
        depends_on: list[str] | None = None,
    ) -> None:
        node = TaskNode(
            task_id=task_id,
            task_name=task_name,
            label=label or task_name,
            status="pending",
            children=depends_on or [],
        )
        self._tracker.add_node(pipeline_id, node)

    def start_task(self, pipeline_id: str, task_id: str) -> None:
        self._tracker.complete_node(pipeline_id, task_id, "running")

    def complete_task(self, pipeline_id: str, task_id: str, error: str | None = None) -> None:
        status = "failed" if error else "completed"
        self._tracker.complete_node(pipeline_id, task_id, status, error)

    def get_pipeline(self, pipeline_id: str) -> PipelineDTO | None:
        pipeline = self._tracker.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        return PipelineDTO(
            pipeline_id=pipeline.pipeline_id,
            name=pipeline.name,
            description=pipeline.description,
            nodes=[
                TaskNodeDTO(
                    task_id=n.task_id,
                    task_name=n.task_name,
                    label=n.label,
                    status=n.status,
                    started_at=n.started_at,
                    completed_at=n.completed_at,
                    duration_sec=n.duration_sec,
                    error=n.error,
                )
                for n in pipeline.nodes
            ],
            root_task_ids=pipeline.root_task_ids,
        )

    def list_pipelines(self) -> list[PipelineSummaryDTO]:
        pipelines = self._tracker.list_active_pipelines()
        return [self._format_summary(p) for p in pipelines]

    def get_dag_json(self, pipeline_id: str) -> DagGraphDTO:
        pipeline = self._tracker.get_pipeline(pipeline_id)
        if not pipeline:
            return DagGraphDTO(nodes=[], edges=[])

        nodes = []
        edges = []

        for node in pipeline.nodes:
            color = (
                "#4CAF50"
                if node.status == "completed"
                else "#FF9800"
                if node.status == "running"
                else "#F44336"
                if node.status == "failed"
                else "#9E9E9E"
            )

            nodes.append(
                DagNodeDTO(
                    id=node.task_id,
                    label=node.label,
                    status=node.status,
                    color=color,
                    duration=node.duration_sec,
                )
            )

            for child in node.children:
                edges.append(DagEdgeDTO(source=node.task_id, target=child))

        return DagGraphDTO(nodes=nodes, edges=edges)

    def _format_summary(self, pipeline: TaskPipeline) -> PipelineSummaryDTO:
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        for node in pipeline.nodes:
            if node.status in status_counts:
                status_counts[node.status] += 1

        return PipelineSummaryDTO(
            pipeline_id=pipeline.pipeline_id,
            name=pipeline.name,
            total_tasks=len(pipeline.nodes),
            status=status_counts,
        )

    @property
    def observer(self):
        return self._observer
