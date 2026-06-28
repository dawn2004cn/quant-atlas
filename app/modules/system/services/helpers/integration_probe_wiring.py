from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.integration_probe_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.integration_probe_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)



from app.domain.ports.integration_probe_port import IntegrationProbePort

_port: IntegrationProbePort | None = None
def bind_integration_probe_port(port: IntegrationProbePort | None) -> None:
    global _port
    _port = port
def get_integration_probe_port() -> IntegrationProbePort | None:
    return _port
def require_integration_probe_port() -> IntegrationProbePort:
    if _port is None:
        raise RuntimeError(
            "IntegrationProbePort not configured; bootstrap must call bind_integration_probe_port()"
        )
    return _port
