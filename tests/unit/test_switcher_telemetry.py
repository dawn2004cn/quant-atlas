"""Unit tests for switcher telemetry endpoint.

Tests:
- Valid POST returns 204 and writes JSONL
- Invalid event type returns 400
- Rate limiting returns 429 when exceeded
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

# Werkzeug 3 removed __version__; Flask test_client needs it for HTTP_USER_AGENT.
import werkzeug
if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Minimal Flask app fixture for testing the telemetry endpoint
# ---------------------------------------------------------------------------


def _create_test_app():
    """Create a minimal Flask app with just the telemetry blueprint."""
    from flask import Flask, Blueprint

    from app.presentation.api.routes_v1_telemetry import register_telemetry_routes

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"

    bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_telemetry_routes(bp, ctx=None)
    app.register_blueprint(bp)

    return app


@pytest.fixture
def client():
    """Flask test client for telemetry endpoint."""
    app = _create_test_app()
    # Reset rate limiter state between tests
    import app.presentation.api.routes_v1_telemetry as mod
    mod._ip_counts.clear()
    with app.test_client() as c:
        yield c


@pytest.fixture
def telemetry_dir(tmp_path):
    """Override the telemetry directory to a temp path."""
    telemetry_file = tmp_path / "telemetry.jsonl"
    import app.presentation.api.routes_v1_telemetry as mod

    original_dir = mod._TELEMETRY_DIR
    original_file = mod._TELEMETRY_FILE
    mod._TELEMETRY_DIR = tmp_path
    mod._TELEMETRY_FILE = telemetry_file
    yield tmp_path
    mod._TELEMETRY_DIR = original_dir
    mod._TELEMETRY_FILE = original_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTelemetryEndpoint:
    """Tests for POST /api/v1/telemetry/switcher."""

    def test_valid_switch_to_spa_returns_204(self, client, telemetry_dir):
        """Valid switch_to_spa event returns 204 No Content."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa", "page": "dashboard"},
        )
        assert resp.status_code == 204

    def test_valid_back_to_classic_returns_204(self, client, telemetry_dir):
        """Valid back_to_classic event returns 204 No Content."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "back_to_classic", "page": "backtest"},
        )
        assert resp.status_code == 204

    def test_writes_jsonl(self, client, telemetry_dir):
        """Event is written to telemetry.jsonl with correct structure."""
        client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa", "page": "dashboard", "user_id": "u123"},
        )
        telemetry_file = telemetry_dir / "telemetry.jsonl"
        assert telemetry_file.exists()
        lines = telemetry_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "switch_to_spa"
        assert entry["page"] == "dashboard"
        assert entry["user_id"] == "u123"
        assert "timestamp" in entry

    def test_writes_jsonl_null_user_id(self, client, telemetry_dir):
        """Event without user_id writes null."""
        client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa", "page": "strategy"},
        )
        telemetry_file = telemetry_dir / "telemetry.jsonl"
        entry = json.loads(telemetry_file.read_text(encoding="utf-8").strip())
        assert entry["user_id"] is None

    def test_invalid_event_returns_400(self, client, telemetry_dir):
        """Invalid event type returns 400 with error details."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "invalid_event", "page": "dashboard"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "invalid_event" in data["error"]

    def test_missing_page_returns_400(self, client, telemetry_dir):
        """Missing page field returns 400."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa"},
        )
        assert resp.status_code == 400

    def test_empty_page_returns_400(self, client, telemetry_dir):
        """Empty page string returns 400."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa", "page": "  "},
        )
        assert resp.status_code == 400

    def test_rate_limiting_returns_429(self, client, telemetry_dir):
        """Exceeding 10 requests/second returns 429."""
        for _ in range(10):
            resp = client.post(
                "/api/v1/telemetry/switcher",
                json={"event": "switch_to_spa", "page": "dashboard"},
            )
            assert resp.status_code == 204
        resp = client.post(
            "/api/v1/telemetry/switcher",
            json={"event": "switch_to_spa", "page": "dashboard"},
        )
        assert resp.status_code == 429

    def test_no_body_returns_400(self, client, telemetry_dir):
        """Request with no JSON body returns 400."""
        resp = client.post(
            "/api/v1/telemetry/switcher",
            data="",
            content_type="application/json",
        )
        # Empty body → event=None → invalid_event 400
        assert resp.status_code == 400