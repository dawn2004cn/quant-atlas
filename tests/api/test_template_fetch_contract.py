"""Template fetch('/api/v1/...') paths must match Flask url_map rules."""

from __future__ import annotations

from app.presentation.api.route_contract import (
    CRITICAL_ROUTE_MODULES,
    LEGACY_PATH_ALIASES,
    collect_template_fetch_paths,
    missing_canonical_paths,
    missing_template_fetch_paths,
    path_registered_in_rules,
)


def test_template_fetch_paths_registered(flask_app):
    """Every literal template fetch path resolves to a Flask rule."""
    missing = missing_template_fetch_paths(flask_app.url_map)
    assert not missing, "unregistered template fetch paths: " + ", ".join(missing[:15])


def test_critical_canonical_paths_registered(flask_app):
    """All CRITICAL_ROUTE_MODULES paths exist after boot."""
    missing = missing_canonical_paths(flask_app.url_map)
    assert not missing, "missing canonical paths: " + ", ".join(missing)


def test_legacy_alias_targets_exist(flask_app):
    """Legacy alias canonical targets must exist before aliases attach."""
    rules = [r.rule for r in flask_app.url_map.iter_rules()]
    for _alias, canonical in LEGACY_PATH_ALIASES:
        assert path_registered_in_rules(rules, canonical), f"missing alias target {canonical}"


def test_template_fetch_collection_non_empty():
    """Sanity: templates declare at least some /api/v1 fetch calls."""
    paths = collect_template_fetch_paths()
    assert len(paths) >= 50


def test_critical_module_count_grew():
    """Guard against accidental shrink of the contract registry."""
    assert len(CRITICAL_ROUTE_MODULES) >= 12
