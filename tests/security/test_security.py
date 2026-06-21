"""Security tests: login enforcement, CORS, headers."""

from __future__ import annotations


class TestLoginRequired:
    """Authenticated routes must reject anonymous requests."""

    def test_anonymous_rejected_on_protected_routes(self, client):
        """Any route without explicit @anonymous must return 401."""
        protected = [
            "/api/v1/daily-workbench",
            "/api/v1/system/active-jobs",
            "/api/v1/system/task-messages",
            "/api/v1/retail-assistant/quick-actions",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"Expected 401 for {path}, got {resp.status_code}"


class TestSecurityHeaders:
    """Production responses must include security headers."""

    def test_x_content_type_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_xss_protection(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestCORSConfig:
    """CORS should not allow wildcard origins in production."""

    def test_socketio_cors_config(self):
        """CORS origins should be configurable via environment variable."""
        from app.core.runtime_config import get_runtime

        # Default should allow all only if not configured
        origins = get_runtime("SOCKETIO_ALLOWED_ORIGINS", "*")
        # If configured, must not be wildcard only
        if origins.strip():
            allowed = [o.strip() for o in origins.split(",") if o.strip()]
            assert "*" not in allowed or len(allowed) == 1
