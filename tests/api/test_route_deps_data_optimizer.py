"""Data optimizer route deps tests."""

from __future__ import annotations

from types import SimpleNamespace

from app.presentation.api.route_deps import build_data_optimizer_route_deps


def test_build_data_optimizer_route_deps():
    ctx = SimpleNamespace(enable_legacy_response_fields=False)
    deps = build_data_optimizer_route_deps(ctx)
    assert deps.enable_legacy_response_fields is False
