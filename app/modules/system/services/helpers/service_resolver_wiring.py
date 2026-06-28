from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.service_resolver_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.service_resolver_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound optional service resolver for application lazy wiring."""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_resolve_optional: Callable[[type[T]], T | None] | None = None
def bind_service_resolver(resolver: Callable[[type[T]], T | None]) -> None:
    global _resolve_optional
    _resolve_optional = resolver
def resolve_optional_service(interface: type[T]) -> T | None:
    if _resolve_optional is None:
        raise RuntimeError("Service resolver not configured; bootstrap must bind it")
    return _resolve_optional(interface)
