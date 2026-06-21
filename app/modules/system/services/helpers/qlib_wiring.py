from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.qlib_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.qlib_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound Qlib infrastructure factories for application services."""

from collections.abc import Callable
from typing import Any
from app.domain.ports.qlib_bin_dumper_port import QlibBinDumperPort
from app.domain.ports.qlib_task_ports import QlibTaskService


_create_data_adapter: Callable[..., Any] | None = None
_bin_dumper: QlibBinDumperPort | None = None
_task_service_factory: Callable[[], QlibTaskService] | None = None
def bind_qlib_infrastructure(
    *,
    create_data_adapter: Callable[..., Any],
    bin_dumper: QlibBinDumperPort,
    task_service_factory: Callable[[], QlibTaskService],
) -> None:
    global _create_data_adapter, _bin_dumper, _task_service_factory
    _create_data_adapter = create_data_adapter
    _bin_dumper = bin_dumper
    _task_service_factory = task_service_factory
def create_qlib_data_adapter(data_access: Any, **kwargs: Any) -> Any:
    if _create_data_adapter is None:
        raise RuntimeError("Qlib infrastructure not configured; bootstrap must bind it")
    return _create_data_adapter(data_access, **kwargs)
def get_qlib_bin_dumper() -> QlibBinDumperPort:
    if _bin_dumper is None:
        raise RuntimeError("Qlib bin dumper not configured; bootstrap must bind it")
    return _bin_dumper
def create_qlib_task_service() -> QlibTaskService:
    if _task_service_factory is None:
        raise RuntimeError("Qlib task service factory not configured; bootstrap must bind it")
    return _task_service_factory()
