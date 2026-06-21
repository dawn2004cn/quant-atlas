from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TaskNodeDTO(BaseModel):
    task_id: str
    task_name: str
    label: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_sec: Optional[float] = None
    error: Optional[str] = None

class PipelineDTO(BaseModel):
    pipeline_id: str
    name: str
    description: str
    nodes: List[TaskNodeDTO]
    root_task_ids: List[str]

class PipelineSummaryDTO(BaseModel):
    pipeline_id: str
    name: str
    total_tasks: int
    status: Dict[str, int]

class DagNodeDTO(BaseModel):
    id: str
    label: str
    status: str
    color: str
    duration: Optional[float] = None

class DagEdgeDTO(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")

class DagGraphDTO(BaseModel):
    nodes: List[DagNodeDTO]
    edges: List[DagEdgeDTO]
