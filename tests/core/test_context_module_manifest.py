"""Context module manifest from registry."""

from __future__ import annotations

from app.core.registry import context_module_manifest, discover_modules


def test_context_module_manifest_lists_modules():
    payload = context_module_manifest()
    assert payload["schema_version"] == "v2"
    assert payload["module_count"] >= 1
    names = {m["name"] for m in payload["modules"]}
    assert "system" in names or "market_data" in names


def test_discover_modules_includes_collaboration_when_enabled():
    modules = discover_modules(config={"ENABLE_COLLABORATION": True})
    names = {m.name for m in modules}
    assert "collaboration" in names or "portfolio_risk" in names or "system" in names
