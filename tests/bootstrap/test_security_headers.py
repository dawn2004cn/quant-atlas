"""CSP nonce header must use quoted nonce sources for inline styles to apply."""

from __future__ import annotations

import re

import pytest


@pytest.fixture()
def client():
    import werkzeug

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    with app.test_client() as c:
        yield c


def test_login_page_csp_nonce_quoted(client) -> None:
    resp = client.get("/login")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "'nonce-" in csp
    match = re.search(r"'nonce-([a-f0-9]+)'", csp)
    assert match is not None
    nonce = match.group(1)
    body = resp.get_data(as_text=True)
    assert f'nonce="{nonce}"' in body


def test_style_src_allows_inline_styles(client) -> None:
    """Page <style> blocks and style=\"\" attrs must not be blocked by CSP."""
    csp = client.get("/login").headers.get("Content-Security-Policy", "")
    assert "style-src" in csp
    style_part = [p.strip() for p in csp.split(";") if "style-src" in p][0]
    assert "'unsafe-inline'" in style_part
    assert "'nonce-" not in style_part


def test_login_page_has_login_shell_styles(client) -> None:
    body = client.get("/login").get_data(as_text=True)
    assert "login-shell" in body
    assert ".hero {" in body
    assert "linear-gradient" in body
