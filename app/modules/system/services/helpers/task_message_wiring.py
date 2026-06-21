from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.task_message_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.task_message_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound task message store for application services."""

from collections.abc import Callable
from typing import Any


_store_factory: Callable[[], Any] | None = None
def bind_task_message_store(factory: Callable[[], Any]) -> None:
    global _store_factory
    _store_factory = factory
def get_task_message_store() -> Any:
    if _store_factory is None:
        raise RuntimeError("Task message store not configured; bootstrap must bind it")
    return _store_factory()
