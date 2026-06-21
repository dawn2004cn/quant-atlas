"""API rate limit middleware tests."""

from __future__ import annotations

import werkzeug
from flask import Flask

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

from app.core.middleware.api_rate_limit import init_api_rate_limit_middleware


def test_api_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("API_RATE_LIMIT_RPM", "1")

    app = Flask(__name__)
    app.config["TESTING"] = False

    @app.get("/api/v1/ping")
    def ping():
        return {"ok": True}

    init_api_rate_limit_middleware(app)

    with app.test_client() as client:
        assert client.get("/api/v1/ping").status_code == 200
        assert client.get("/api/v1/ping").status_code == 429


def test_health_path_exempt(monkeypatch) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("API_RATE_LIMIT_RPM", "1")

    app = Flask(__name__)
    app.config["TESTING"] = False

    @app.get("/api/v1/system/health")
    def health():
        return {"ok": True}

    init_api_rate_limit_middleware(app)

    with app.test_client() as client:
        assert client.get("/api/v1/system/health").status_code == 200
        assert client.get("/api/v1/system/health").status_code == 200
