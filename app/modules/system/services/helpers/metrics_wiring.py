from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.metrics_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.metrics_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound Prometheus metrics helpers for presentation metrics routes."""

from collections.abc import Callable
from typing import Any


_get_metrics: Callable[[], bytes] | None = None
_get_metrics_content_type: Callable[[], str] | None = None
_get_metrics_summary: Callable[[], dict[str, Any]] | None = None
def bind_metrics_infrastructure(
    *,
    get_metrics: Callable[[], bytes],
    get_metrics_content_type: Callable[[], str],
    get_metrics_summary: Callable[[], dict[str, Any]],
) -> None:
    global _get_metrics, _get_metrics_content_type, _get_metrics_summary
    _get_metrics = get_metrics
    _get_metrics_content_type = get_metrics_content_type
    _get_metrics_summary = get_metrics_summary
def render_prometheus_metrics() -> bytes:
    if _get_metrics is None:
        raise RuntimeError("Metrics infrastructure not configured; bootstrap must bind it")
    return _get_metrics()
def prometheus_metrics_content_type() -> str:
    if _get_metrics_content_type is None:
        raise RuntimeError("Metrics infrastructure not configured; bootstrap must bind it")
    return _get_metrics_content_type()
def build_metrics_summary() -> dict[str, Any]:
    if _get_metrics_summary is None:
        raise RuntimeError("Metrics infrastructure not configured; bootstrap must bind it")
    return _get_metrics_summary()
