"""Smoke: critical API paths exist after boot."""

from __future__ import annotations

import pytest

from app.presentation.api.route_contract import path_registered_in_rules


KEY_API_PATHS = (
    "/api/v1/global/quote",
    "/api/v1/global/history",
    "/api/v1/markets/CN/quotes",
    "/api/v1/markets/CN/quotes/page",
    "/api/v1/system/task-messages",
    "/api/v1/quotes",
    "/api/v1/compliance/manifest",
    "/api/v1/jarvis/proactive",
)


@pytest.mark.parametrize("path", KEY_API_PATHS)
def test_critical_api_path_registered(flask_app, path: str):
    rules = [rule.rule for rule in flask_app.url_map.iter_rules()]
    assert path_registered_in_rules(rules, path), f"missing route: {path}"
