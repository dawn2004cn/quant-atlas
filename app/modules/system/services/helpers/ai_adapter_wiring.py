from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.ai_adapter_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.ai_adapter_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound AI analysis adapter for application services."""

from collections.abc import Callable

from app.domain.ports.ai_analysis_port import AiAnalysisPort

_create_ai_analysis: Callable[[], AiAnalysisPort] | None = None
def bind_ai_analysis_infrastructure(*, adapter_factory: Callable[[], AiAnalysisPort]) -> None:
    global _create_ai_analysis
    _create_ai_analysis = adapter_factory
def create_ai_analysis_adapter() -> AiAnalysisPort:
    if _create_ai_analysis is None:
        raise RuntimeError("AI analysis infrastructure not configured; bootstrap must bind it")
    return _create_ai_analysis()
