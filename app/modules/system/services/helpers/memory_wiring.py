from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.memory_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.memory_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound shared memory manager for application services."""

from collections.abc import Callable
from typing import Any

_get_memory_manager: Callable[[], Any] | None = None
def bind_memory_infrastructure(*, manager_factory: Callable[[], Any]) -> None:
    global _get_memory_manager
    _get_memory_manager = manager_factory
def get_shared_memory_manager() -> Any:
    if _get_memory_manager is None:
        raise RuntimeError("Memory infrastructure not configured; bootstrap must bind it")
    return _get_memory_manager()
