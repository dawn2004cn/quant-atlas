from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.pytdx_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.pytdx_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound Pytdx market port for application services (configured at bootstrap)."""

from app.domain.ports.pytdx_port import PytdxMarketPort


_port: PytdxMarketPort | None = None
def bind_pytdx_market_port(port: PytdxMarketPort) -> None:
    global _port
    _port = port
def get_pytdx_market_port() -> PytdxMarketPort:
    if _port is None:
        raise RuntimeError(
            "PytdxMarketPort not configured; bootstrap must call bind_pytdx_market_port()"
        )
    return _port
