from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.events_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.events_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound event store and integration event emitters for application services."""

from collections.abc import Callable
from typing import Any

_event_store_factory: Callable[[], Any] | None = None
_integration_events_factory: Callable[[], Any] | None = None
def bind_event_infrastructure(
    *,
    event_store_factory: Callable[[], Any],
    integration_events_factory: Callable[[], Any],
) -> None:
    global _event_store_factory, _integration_events_factory
    _event_store_factory = event_store_factory
    _integration_events_factory = integration_events_factory
def get_default_event_store() -> Any:
    if _event_store_factory is None:
        raise RuntimeError("Event infrastructure not configured; bootstrap must bind it")
    return _event_store_factory()
def get_default_integration_events() -> Any:
    if _integration_events_factory is None:
        raise RuntimeError("Event infrastructure not configured; bootstrap must bind it")
    return _integration_events_factory()
