from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    STOCK_RESEARCH = "stock_research"
    STRATEGY_BACKTEST = "strategy_backtest"
    DAILY_SYNC = "daily_sync"
    SIGNAL_SCAN = "signal_scan"


@dataclass
class WorkflowInstance:
    workflow_id: str
    type: WorkflowType
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress: int = 0
    user_id: int | None = None
    params: dict[str, Any] = field(default_factory=dict)
    current_step: str | None = None
    evidence: list[str] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now()


@dataclass
class WorkflowCheckpoint:
    checkpoint_id: str
    workflow_id: str
    step: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
