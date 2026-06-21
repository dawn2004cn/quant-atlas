from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.domain.workflow_hub.models import (
    WorkflowCheckpoint,
    WorkflowInstance,
    WorkflowStatus,
)
from app.domain.workflow_hub.ports import WorkflowRepository


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, WorkflowInstance] = {}
        self._checkpoints: dict[str, list[WorkflowCheckpoint]] = defaultdict(list)

    def save(self, instance: WorkflowInstance) -> None:
        with self._lock:
            self._items[instance.workflow_id] = instance

    def get(self, workflow_id: str) -> WorkflowInstance | None:
        with self._lock:
            return self._items.get(workflow_id)

    def list_active(self, user_id: int | None = None) -> list[WorkflowInstance]:
        with self._lock:
            out = []
            for wf in self._items.values():
                if wf.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING, WorkflowStatus.WAITING):
                    if user_id is None or wf.user_id == user_id:
                        out.append(wf)
            out.sort(key=lambda w: w.updated_at, reverse=True)
            return out

    def update_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        progress: int = 0,
        error: str | None = None,
    ) -> WorkflowInstance | None:
        with self._lock:
            wf = self._items.get(workflow_id)
            if wf is None:
                return None
            wf.status = status
            wf.progress = progress
            if error is not None:
                wf.error = error
            wf.touch()
            if status == WorkflowStatus.COMPLETED:
                wf.completed_at = datetime.now()
            return wf

    def add_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        with self._lock:
            self._checkpoints[checkpoint.workflow_id].append(checkpoint)

    def list_checkpoints(self, workflow_id: str) -> list[WorkflowCheckpoint]:
        with self._lock:
            return list(self._checkpoints.get(workflow_id, []))
