"""Intent Decomposer domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepType(str, Enum):
    FETCH_DATA = "fetch_data"
    CALCULATE = "calculate"
    ARBITER_REVIEW = "arbiter_review"
    OPTIMIZE = "optimize"
    NOTIFY = "notify"
    STORE = "store"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    step_id: str
    step_type: StepType
    label: str
    description: str
    status: StepStatus = StepStatus.PENDING
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def touch(self) -> None:
        self.started_at = datetime.now()


@dataclass
class ExecutionPlan:
    plan_id: str
    intent: str
    symbol: str = ""
    market: str = "ALL"
    steps: list[ExecutionStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
