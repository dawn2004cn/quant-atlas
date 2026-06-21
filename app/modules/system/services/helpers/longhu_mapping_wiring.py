from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.longhu_mapping_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.longhu_mapping_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound longhu mapping port for application services."""

from app.domain.ports.longhu_mapping_port import LonghuMappingPort


_port: LonghuMappingPort | None = None
def bind_longhu_mapping_port(port: LonghuMappingPort) -> None:
    global _port
    _port = port
def get_longhu_mapping_port() -> LonghuMappingPort:
    if _port is None:
        raise RuntimeError(
            "LonghuMappingPort not configured; bootstrap must call bind_longhu_mapping_port()"
        )
    return _port
