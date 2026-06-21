from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.market_data_ingestor_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.market_data_ingestor_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound longhu market data ingestor factory."""

from collections.abc import Callable
from app.domain.ports.market_data_ports import IMarketDataIngestor


_factory: Callable[[], IMarketDataIngestor] | None = None
def bind_longhu_ingestor_factory(factory: Callable[[], IMarketDataIngestor]) -> None:
    global _factory
    _factory = factory
def create_longhu_ingestor() -> IMarketDataIngestor:
    if _factory is None:
        raise RuntimeError(
            "Longhu ingestor factory not configured; bootstrap must call bind_longhu_ingestor_factory()"
        )
    return _factory()
