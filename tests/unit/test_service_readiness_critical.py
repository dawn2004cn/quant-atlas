"""Critical service resolution smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.bootstrap_components.service_readiness import (
    CRITICAL_RESOLVE_SERVICES,
    resolve_all_critical_services,
)


def test_resolve_all_critical_services_ok():
    registry = MagicMock()
    registry.get_or_none.side_effect = lambda name: object()
    report = resolve_all_critical_services(registry, strict=False)
    assert report.ok
    assert set(report.resolved) == set(CRITICAL_RESOLVE_SERVICES)


def test_resolve_all_critical_services_missing():
    registry = MagicMock()
    registry.get_or_none.return_value = None
    registry.get.side_effect = Exception("missing")
    report = resolve_all_critical_services(registry, strict=False)
    assert not report.ok
    assert len(report.missing) == len(CRITICAL_RESOLVE_SERVICES)
