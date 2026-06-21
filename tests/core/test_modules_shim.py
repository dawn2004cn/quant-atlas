"""Legacy modules shim delegates to registry manifest."""

from __future__ import annotations

from app.core.modules import module_manifest
from app.core.registry import context_module_manifest


def test_module_manifest_delegates_to_context_module_manifest():
    assert module_manifest() == context_module_manifest()
