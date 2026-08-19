"""Public vs protected API v1 contract tests."""

from __future__ import annotations

import pytest

from app.presentation.api.public_api_paths import PUBLIC_API_V1_GET_PATHS, is_public_api_v1_path


@pytest.mark.parametrize("path", sorted(PUBLIC_API_V1_GET_PATHS))
def test_public_paths_allow_anonymous_get(client, path: str):
    """Documented public endpoints return 200 without session."""
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} should be public, got {resp.status_code}"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/system/task-messages",
        "/api/v1/system/active-jobs",
        "/api/v1/jarvis/proactive",
        "/api/v1/integration/stack-status",
    ],
)
def test_protected_paths_reject_anonymous_get(client, path: str):
    """Sensitive dashboards require authentication."""
    assert not is_public_api_v1_path(path)
    resp = client.get(path)
    assert resp.status_code == 401, f"{path} should require login"


def test_compliance_manifest_payload_shape(client):
    resp = client.get("/api/v1/compliance/manifest")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body is not None
    data = body.get("data") or body
    assert "disclaimers" in data


def test_health_includes_realtime_capabilities(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body is not None
    rt = body.get("realtime")
    assert isinstance(rt, dict)
    assert "socketio_available" in rt
    assert "gateway_mode" in rt


def test_public_registry_covers_compliance_manifest():
    assert "/api/v1/compliance/manifest" in PUBLIC_API_V1_GET_PATHS
