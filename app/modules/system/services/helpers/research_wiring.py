from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.research_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.research_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound research workflow adapter for application services."""

from collections.abc import Callable
from typing import Any

from app.domain.ports.research_port import ResearchPort

_create_research_port: Callable[..., ResearchPort] | None = None
def bind_research_infrastructure(*, research_port_factory: Callable[..., ResearchPort]) -> None:
    global _create_research_port
    _create_research_port = research_port_factory
def create_trading_agents_research_port(*, fingpt_application_service: Any = None) -> ResearchPort:
    if _create_research_port is None:
        raise RuntimeError("Research infrastructure not configured; bootstrap must bind it")
    return _create_research_port(fingpt_application_service=fingpt_application_service)
