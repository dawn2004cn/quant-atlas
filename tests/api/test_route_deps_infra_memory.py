"""Memory / task-pipeline / data-infra route deps tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import (
    build_data_infrastructure_route_deps,
    build_memory_route_deps,
    build_task_pipeline_route_deps,
)


def test_build_memory_route_deps():
    svc = object()
    ctx = SimpleNamespace(memory_optimization_service=svc)
    assert build_memory_route_deps(ctx).memory_optimization_service is svc


def test_build_task_pipeline_route_deps():
    svc = object()
    ctx = SimpleNamespace(task_pipeline_service=svc)
    assert build_task_pipeline_route_deps(ctx).task_pipeline_service is svc


def test_build_data_infrastructure_route_deps():
    svc = object()
    ctx = SimpleNamespace(
        data_infrastructure_service=svc,
        task_dispatcher=object(),
        task_message_store=None,
        enable_legacy_response_fields=False,
    )
    deps = build_data_infrastructure_route_deps(ctx)
    assert deps.data_infrastructure_service is svc


def test_build_data_infrastructure_route_deps_missing_raises():
    ctx = SimpleNamespace(
        data_infrastructure_service=None,
        task_dispatcher=None,
        task_message_store=None,
        enable_legacy_response_fields=True,
    )
    with pytest.raises(ValidationError, match="data_infrastructure_service_unavailable"):
        build_data_infrastructure_route_deps(ctx)
