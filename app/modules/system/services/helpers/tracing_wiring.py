from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.tracing_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.tracing_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound tracing helpers for application services."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


_create_span: Callable[..., AbstractContextManager[Any]] | None = None
def bind_tracing(*, create_span: Callable[..., AbstractContextManager[Any]]) -> None:
    global _create_span
    _create_span = create_span
def create_span(name: str, **kwargs: Any) -> AbstractContextManager[Any]:
    if _create_span is None:
        raise RuntimeError("Tracing not configured; bootstrap must bind it")
    return _create_span(name, **kwargs)
