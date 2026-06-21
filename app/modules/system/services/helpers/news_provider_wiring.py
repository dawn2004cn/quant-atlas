from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.news_provider_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.news_provider_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound news provider for application services."""

from app.domain.ports.market_ports import NewsProvider


_provider: NewsProvider | None = None
def bind_news_provider(provider: NewsProvider) -> None:
    global _provider
    _provider = provider
def get_news_provider() -> NewsProvider:
    if _provider is None:
        raise RuntimeError(
            "NewsProvider not configured; bootstrap must call bind_news_provider()"
        )
    return _provider
