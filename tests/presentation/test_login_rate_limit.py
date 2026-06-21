"""Login page rate limit should not count GET refreshes."""

from __future__ import annotations

import werkzeug


def test_login_get_does_not_consume_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)

    from app.bootstrap import create_app
    from app.presentation.web import auth as auth_module

    auth_module._login_limiter.reset("127.0.0.1")
    app = create_app()
    app.config["TESTING"] = False
    client = app.test_client()

    for _ in range(10):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"login-retry-countdown" not in resp.data

    auth_module._login_limiter.reset("127.0.0.1")


def test_login_failed_post_shows_countdown(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)

    from app.bootstrap import create_app
    from app.presentation.web import auth as auth_module

    auth_module._login_limiter.reset("127.0.0.1")
    app = create_app()
    app.config["TESTING"] = False
    client = app.test_client()

    client.get("/login")
    with client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token")
    assert csrf_token

    for _ in range(auth_module._LOGIN_RATE_MAX_ATTEMPTS):
        client.post(
            "/login",
            data={
                "username": "admin",
                "password": "wrong-password",
                "csrf_token": csrf_token,
            },
        )

    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"login-retry-countdown" in resp.data
    assert b"disabled" in resp.data

    auth_module._login_limiter.reset("127.0.0.1")
