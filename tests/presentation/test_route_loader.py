"""Tests for Phase 2 registry route preloading."""

from __future__ import annotations

import pytest

from app.core.registry import clear_route_registry, registered_route_names
from app.presentation.api.route_loader import preload_route_modules


@pytest.fixture(autouse=True)
def _isolate_route_registry():
    clear_route_registry()
    yield
    clear_route_registry()


def test_preload_route_modules_populates_registry():
    before = len(registered_route_names())
    loaded = preload_route_modules()
    after = len(registered_route_names())

    assert loaded > 0
    assert after > before
    assert "collaboration" in registered_route_names()
    assert "health" in registered_route_names()
    assert "quant_ai" in registered_route_names()
    assert "sentiment" in registered_route_names()
    assert "portfolio_user" in registered_route_names()


def test_collaboration_route_uses_collaboration_context():
    import importlib

    mod = importlib.import_module("app.presentation.api.routes_v1_collaboration")
    importlib.reload(mod)
    from app.core.registry import _route_registry

    entry = _route_registry.get("collaboration")
    assert entry is not None
    assert entry["context"] == "collaboration"
