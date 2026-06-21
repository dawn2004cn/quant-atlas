"""Authenticated API POST requests require CSRF header."""

from __future__ import annotations

from app.bootstrap import create_app


def _login(client) -> None:
    with client.session_transaction() as sess:
        sess["_user_id"] = "1"
        sess["_fresh"] = True
        sess["csrf_token"] = "test-csrf-token"


def test_authenticated_api_post_rejects_missing_csrf() -> None:
    app = create_app()
    with app.test_client() as client:
        _login(client)
        res = client.post(
            "/api/v1/signal-flag/scan",
            json={"max_stocks": 1},
        )
        assert res.status_code == 403
        assert res.get_json().get("error") == "CSRF token missing or invalid"


def test_authenticated_api_post_accepts_csrf_header() -> None:
    app = create_app()
    with app.test_client() as client:
        _login(client)
        res = client.post(
            "/api/v1/signal-flag/scan",
            json={"max_stocks": 1},
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert res.status_code != 403
