from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.task_pipeline_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.task_pipeline_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound task pipeline infrastructure for application services."""

from collections.abc import Callable
from typing import Any

from app.domain.ports.task_pipeline_ports import TaskPipelinePort

_create_pipeline: Callable[[], TaskPipelinePort] | None = None
_create_observer: Callable[[TaskPipelinePort], Any] | None = None
def bind_task_pipeline_infrastructure(
    *,
    pipeline_factory: Callable[[], TaskPipelinePort],
    observer_factory: Callable[[TaskPipelinePort], Any],
) -> None:
    global _create_pipeline, _create_observer
    _create_pipeline = pipeline_factory
    _create_observer = observer_factory
def create_default_task_pipeline() -> TaskPipelinePort:
    if _create_pipeline is None:
        raise RuntimeError("Task pipeline infrastructure not configured; bootstrap must bind it")
    return _create_pipeline()
def create_task_observer(tracker: TaskPipelinePort) -> Any:
    if _create_observer is None:
        raise RuntimeError("Task pipeline infrastructure not configured; bootstrap must bind it")
    return _create_observer(tracker)
