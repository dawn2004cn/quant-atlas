"""Session cookie Secure flag must not break HTTP development login."""

from __future__ import annotations

from app.bootstrap import _build_flask_app
from app.config.app_settings import AppEnvironment, AppSettings


def test_session_cookie_secure_defaults_off_outside_production(monkeypatch) -> None:
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    settings = AppSettings(
        secret_key="test-secret-key-for-cookie-policy",
        debug=False,
        environment=AppEnvironment.DEVELOPMENT,
    )
    app = _build_flask_app(settings)
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_session_cookie_secure_defaults_on_in_production(monkeypatch) -> None:
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    settings = AppSettings(
        secret_key="test-secret-key-for-cookie-policy",
        debug=False,
        environment=AppEnvironment.PRODUCTION,
    )
    app = _build_flask_app(settings)
    assert app.config["SESSION_COOKIE_SECURE"] is True
