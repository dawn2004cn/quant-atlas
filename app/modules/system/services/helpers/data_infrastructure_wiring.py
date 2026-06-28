from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.data_infrastructure_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.data_infrastructure_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound data infrastructure helpers (quality monitor + lineage tracker)."""

from collections.abc import Callable

from app.domain.ports.data_lineage_port import DataLineagePort
from app.domain.ports.data_quality_ports import DataQualityPort

_create_quality_monitor: Callable[[], DataQualityPort] | None = None
_create_lineage_tracker: Callable[[], DataLineagePort] | None = None
def bind_data_infrastructure(
    *,
    quality_monitor_factory: Callable[[], DataQualityPort],
    lineage_tracker_factory: Callable[[], DataLineagePort],
) -> None:
    global _create_quality_monitor, _create_lineage_tracker
    _create_quality_monitor = quality_monitor_factory
    _create_lineage_tracker = lineage_tracker_factory
def create_default_data_quality_monitor() -> DataQualityPort:
    if _create_quality_monitor is None:
        raise RuntimeError("Data infrastructure not configured; bootstrap must bind it")
    return _create_quality_monitor()
def create_data_lineage_tracker() -> DataLineagePort:
    if _create_lineage_tracker is None:
        raise RuntimeError("Data infrastructure not configured; bootstrap must bind it")
    return _create_lineage_tracker()
