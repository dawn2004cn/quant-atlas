from __future__ import annotations

from abc import ABC, abstractmethod

from .models import WorkflowInstance, WorkflowCheckpoint, WorkflowStatus


class WorkflowRepository(ABC):
    @abstractmethod
    def save(self, instance: WorkflowInstance) -> None: ...

    @abstractmethod
    def get(self, workflow_id: str) -> WorkflowInstance | None: ...

    @abstractmethod
    def list_active(self, user_id: int | None = None) -> list[WorkflowInstance]: ...

    @abstractmethod
    def update_status(
        self, workflow_id: str, status: WorkflowStatus, progress: int = 0, error: str | None = None
    ) -> WorkflowInstance | None: ...

    @abstractmethod
    def add_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None: ...

    @abstractmethod
    def list_checkpoints(self, workflow_id: str) -> list[WorkflowCheckpoint]: ...


class WorkflowEngine(ABC):
    @abstractmethod
    def start(self, wf_type: str, params: dict[str, object], user_id: int | None) -> WorkflowInstance: ...

    @abstractmethod
    def resume(self, workflow_id: str, action: str, payload: dict[str, object] | None = None) -> WorkflowInstance: ...
