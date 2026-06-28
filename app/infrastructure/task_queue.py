from __future__ import annotations

"""
Deprecation shim: ``from app.infrastructure.task_queue import ...`` still works,
but the canonical implementation is now ``PriorityTaskQueue`` in ``task_queue_v2.py``.

All new code should import directly from ``task_queue_v2``:
    from app.infrastructure.task_queue_v2 import PriorityTaskQueue, TaskPriority, TaskStatus
"""

import warnings
from .task_queue_v2 import (  # noqa: F401  (re-export for backward compat)
    PriorityTaskQueue,
    TaskPriority,
    TaskStatus,
    get_task_queue,
    init_task_queue,
    close_task_queue,
)

warnings.warn(
    "app.infrastructure.task_queue is deprecated; use app.infrastructure.task_queue_v2 directly.",
    DeprecationWarning,
    stacklevel=2,
)
