from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.tdx_finance_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.tdx_finance_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound TDX finance snapshot port for application services."""

from app.domain.ports.tdx_finance_port import TdxFinancePort, TdxFinanceSnapshot


_port: TdxFinancePort | None = None
def bind_tdx_finance_port(port: TdxFinancePort) -> None:
    global _port
    _port = port
def fetch_tdx_finance_snapshot(symbol: str) -> TdxFinanceSnapshot | None:
    if _port is None:
        raise RuntimeError("TdxFinancePort not configured; bootstrap must bind it")
    return _port.fetch_snapshot(symbol)
