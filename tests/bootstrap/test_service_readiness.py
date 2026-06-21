"""Tests for bootstrap service readiness tiers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.bootstrap_components.service_readiness import (
    REQUIRED_SERVICE_ATTRS,
    validate_service_readiness,
)


def test_validate_ok_when_required_present():
    services = SimpleNamespace(**{name: object() for name in REQUIRED_SERVICE_ATTRS})
    report = validate_service_readiness(services, strict=False)
    assert report.ok
    assert report.missing_required == ()


def test_validate_strict_raises_when_required_missing(monkeypatch):
    monkeypatch.setenv("STRICT_BOOTSTRAP", "1")
    services = SimpleNamespace(market_service=object())
    with pytest.raises(RuntimeError, match="Bootstrap missing REQUIRED"):
        validate_service_readiness(services, strict=True)
