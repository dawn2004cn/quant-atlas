from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.async_market_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.async_market_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound async market helpers for application services."""

from collections.abc import Callable
from typing import Any


_wrap_sync_provider: Callable[[Any], Any] | None = None
_standalone_factory: Callable[[], Any] | None = None
def bind_async_market_helpers(
    *,
    wrap_sync_provider: Callable[[Any], Any],
    standalone_factory: Callable[[], Any],
) -> None:
    global _wrap_sync_provider, _standalone_factory
    _wrap_sync_provider = wrap_sync_provider
    _standalone_factory = standalone_factory
def wrap_market_provider_for_async(sync_provider: Any) -> Any:
    if _wrap_sync_provider is None:
        raise RuntimeError(
            "Async market helpers not configured; bootstrap must call bind_async_market_helpers()"
        )
    return _wrap_sync_provider(sync_provider)
def get_standalone_async_market_provider() -> Any:
    if _standalone_factory is None:
        raise RuntimeError(
            "Async market helpers not configured; bootstrap must call bind_async_market_helpers()"
        )
    return _standalone_factory()
