from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.tdx_data_repository_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.tdx_data_repository_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)



from app.domain.ports.tdx_data_write_port import TdxBaseDataWritePort, TdxDaykWritePort


_dayk_repo: TdxDaykWritePort | None = None
_base_repo: TdxBaseDataWritePort | None = None
def bind_tdx_dayk_write_port(port: TdxDaykWritePort | None) -> None:
    global _dayk_repo
    _dayk_repo = port
def bind_tdx_base_data_write_port(port: TdxBaseDataWritePort | None) -> None:
    global _base_repo
    _base_repo = port
def get_tdx_dayk_write_port() -> TdxDaykWritePort | None:
    return _dayk_repo
def get_tdx_base_data_write_port() -> TdxBaseDataWritePort | None:
    return _base_repo
def require_tdx_dayk_write_port() -> TdxDaykWritePort:
    if _dayk_repo is None:
        raise RuntimeError(
            "TdxDaykWritePort not configured; bootstrap must call bind_tdx_dayk_write_port()"
        )
    return _dayk_repo
def require_tdx_base_data_write_port() -> TdxBaseDataWritePort:
    if _base_repo is None:
        raise RuntimeError(
            "TdxBaseDataWritePort not configured; bootstrap must call bind_tdx_base_data_write_port()"
        )
    return _base_repo
