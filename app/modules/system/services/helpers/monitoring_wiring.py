from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.monitoring_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.monitoring_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound monitoring helpers for presentation monitoring routes."""

from collections.abc import Callable


_check_table_freshness: Callable[[str, int], bool] | None = None
def bind_monitoring_infrastructure(
    *,
    check_table_freshness: Callable[[str, int], bool],
) -> None:
    global _check_table_freshness
    _check_table_freshness = check_table_freshness
def check_table_freshness(table: str, *, max_delay_minutes: int = 15) -> bool:
    if _check_table_freshness is None:
        raise RuntimeError("Monitoring infrastructure not configured; bootstrap must bind it")
    return _check_table_freshness(table, max_delay_minutes)
