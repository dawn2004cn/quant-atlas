from pydantic import BaseModel, Field

class TaskNodeDTO(BaseModel):
    task_id: str
    task_name: str
    label: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_sec: float | None = None
    error: str | None = None

class PipelineDTO(BaseModel):
    pipeline_id: str
    name: str
    description: str
    nodes: list[TaskNodeDTO]
    root_task_ids: list[str]

class PipelineSummaryDTO(BaseModel):
    pipeline_id: str
    name: str
    total_tasks: int
    status: dict[str, int]

class DagNodeDTO(BaseModel):
    id: str
    label: str
    status: str
    color: str
    duration: float | None = None

class DagEdgeDTO(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")

class DagGraphDTO(BaseModel):
    nodes: list[DagNodeDTO]
    edges: list[DagEdgeDTO]
