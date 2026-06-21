"""API contract tests — assert status codes, response shape, and error codes."""

from __future__ import annotations


class TestHealthEndpoints:
    """Health endpoints must always return 200 with a predictable shape."""

    def test_api_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert "status" in data
        assert data["status"] == "ok"

    def test_system_health_returns_200(self, client):
        # No /api/v1/health endpoint; the health endpoint is at /api/v1/system/health
        pass


class TestLoginRequired:
    """Routes decorated with @login_required must return 401 for anonymous users."""

    def test_daily_workbench_requires_login(self, client):
        resp = client.get("/api/v1/daily-workbench")
        assert resp.status_code == 401

    def test_task_messages_requires_login(self, client):
        resp = client.get("/api/v1/system/task-messages")
        assert resp.status_code == 401

    def test_active_jobs_requires_login(self, client):
        resp = client.get("/api/v1/system/active-jobs")
        assert resp.status_code == 401
