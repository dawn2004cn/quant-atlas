from __future__ import annotations

import json
from typing import Any

from flask import Flask
from flask.testing import FlaskClient


class ApiTestMixin:
    """Mixin class providing helper methods for API endpoint tests.

    Usage::

        class TestMyEndpoint(ApiTestMixin):
            def test_get(self, client):
                resp = self.get_json(client, "/api/v1/my-endpoint")
                assert resp["success"] is True
    """

    def get_json(self, client: FlaskClient, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = client.get(path, **kwargs)
        assert resp.status_code in (200, 201), f"GET {path} returned {resp.status_code}"
        return json.loads(resp.data.decode())

    def post_json(self, client: FlaskClient, path: str, data: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        resp = client.post(path, json=data or {}, **kwargs)
        return json.loads(resp.data.decode())

    def assert_success(self, payload: dict[str, Any], status_code: int = 200) -> None:
        assert payload["success"] is True, f"Expected success=True, got {payload}"
        assert payload["error"] is None

    def assert_error(self, payload: dict[str, Any], expected_code: int = 400) -> None:
        assert payload["success"] is False, f"Expected success=False, got {payload}"
        assert payload["error"] is not None


def create_test_app() -> Flask:
    """Create a minimal test Flask application without full boot."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    app.secret_key = "test-secret-key"
    return app