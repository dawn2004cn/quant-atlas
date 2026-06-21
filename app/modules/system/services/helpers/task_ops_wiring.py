from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.task_ops_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.task_ops_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound Celery inspect/revoke helpers for presentation task-ops routes."""

from collections.abc import Callable
from typing import Any


_inspect_snapshot: Callable[..., dict[str, Any]] | None = None
_task_status: Callable[[str], dict[str, Any]] | None = None
_revoke_task: Callable[..., dict[str, Any]] | None = None
def bind_task_ops_infrastructure(
    *,
    inspect_snapshot: Callable[..., dict[str, Any]],
    task_status: Callable[[str], dict[str, Any]],
    revoke_task: Callable[..., dict[str, Any]],
) -> None:
    global _inspect_snapshot, _task_status, _revoke_task
    _inspect_snapshot = inspect_snapshot
    _task_status = task_status
    _revoke_task = revoke_task
def inspect_celery_snapshot(*, timeout: float = 2.0) -> dict[str, Any]:
    if _inspect_snapshot is None:
        raise RuntimeError("Task ops infrastructure not configured; bootstrap must bind it")
    return _inspect_snapshot(timeout=timeout)
def get_celery_task_status(task_id: str) -> dict[str, Any]:
    if _task_status is None:
        raise RuntimeError("Task ops infrastructure not configured; bootstrap must bind it")
    return _task_status(task_id)
def revoke_celery_task(task_id: str, *, terminate: bool = False) -> dict[str, Any]:
    if _revoke_task is None:
        raise RuntimeError("Task ops infrastructure not configured; bootstrap must bind it")
    return _revoke_task(task_id, terminate=terminate)
