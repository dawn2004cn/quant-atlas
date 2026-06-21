"""FinGPT and recommendation route deps tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import (
    build_fingpt_route_deps,
    build_recommendation_route_deps,
)


def test_build_fingpt_route_deps_ok():
    svc = object()
    ctx = SimpleNamespace(
        fingpt_application_service=svc,
        enable_legacy_response_fields=False,
    )
    deps = build_fingpt_route_deps(ctx)
    assert deps.fingpt_application_service is svc


def test_build_fingpt_route_deps_missing_raises():
    ctx = SimpleNamespace(
        fingpt_application_service=None,
        enable_legacy_response_fields=True,
    )
    with pytest.raises(ValidationError, match="fingpt_application_service_unavailable"):
        build_fingpt_route_deps(ctx)


def test_build_recommendation_route_deps_ok():
    svc = object()
    ctx = SimpleNamespace(
        recommendation_service=svc,
        enable_legacy_response_fields=True,
    )
    deps = build_recommendation_route_deps(ctx)
    assert deps.recommendation_service is svc
