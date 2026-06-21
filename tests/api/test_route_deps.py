"""Tests for narrow API route dependency bundles."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import (
    build_ai_route_deps,
    build_risk_route_deps,
    build_social_route_deps,
    require_moments_service,
    require_swarm_service,
)


def test_build_risk_route_deps_requires_service():
    ctx = SimpleNamespace(risk_service=object(), enable_legacy_response_fields=False)
    deps = build_risk_route_deps(ctx)
    assert deps.risk_service is ctx.risk_service


def test_build_risk_route_deps_missing_raises():
    ctx = SimpleNamespace(risk_service=None, enable_legacy_response_fields=False)
    with pytest.raises(ValidationError, match="risk_service_unavailable"):
        build_risk_route_deps(ctx)


def test_require_moments_service_from_social_group():
    moments = object()
    ctx = SimpleNamespace(
        moments_service=None,
        social=SimpleNamespace(moments_service=moments),
        enable_legacy_response_fields=True,
        enable_celery=False,
        task_dispatcher=None,
        task_message_store=None,
        investment_manager_service=None,
    )
    deps = build_social_route_deps(ctx)
    assert require_moments_service(deps) is moments


def test_build_ai_route_deps_resolves_ai_group_research():
    research = object()
    ctx = SimpleNamespace(
        strategy_service=None,
        prediction_service=None,
        selection_source_service=None,
        ai_analysis_service=None,
        ai_research_service=None,
        ai=SimpleNamespace(ai_research_service=research),
        rdagent_run_service=object(),
        swarm_service=None,
        enable_legacy_response_fields=False,
        enable_qlib=False,
        task_message_store=None,
    )
    deps = build_ai_route_deps(ctx)
    assert deps.ai_research_service is research
    assert require_swarm_service(deps) is ctx.rdagent_run_service
