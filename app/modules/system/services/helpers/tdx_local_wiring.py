from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.tdx_local_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.tdx_local_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound TDX local file port for application services (configured at bootstrap)."""

from app.domain.ports.tdx_local_port import TdxLocalFilePort

_port: TdxLocalFilePort | None = None
def bind_tdx_local_file_port(port: TdxLocalFilePort) -> None:
    global _port
    _port = port
def get_tdx_local_file_port() -> TdxLocalFilePort:
    if _port is None:
        raise RuntimeError(
            "TdxLocalFilePort not configured; bootstrap must call bind_tdx_local_file_port()"
        )
    return _port
