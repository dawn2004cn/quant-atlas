from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.config_loader_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.config_loader_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound config loader port for application services."""

from app.domain.ports.config_loader_port import ConfigLoaderPort

_port: ConfigLoaderPort | None = None
def bind_config_loader_port(port: ConfigLoaderPort) -> None:
    global _port
    _port = port
def get_config_loader_port() -> ConfigLoaderPort:
    if _port is None:
        raise RuntimeError(
            "ConfigLoaderPort not configured; bootstrap must call bind_config_loader_port()"
        )
    return _port
