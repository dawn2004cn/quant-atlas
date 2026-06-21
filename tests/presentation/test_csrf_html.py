"""CSRF HTML helper must render as markup, not escaped text."""

from __future__ import annotations

import werkzeug

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

from markupsafe import Markup

from app.presentation.csrf_protection import _generate_csrf_html


def test_csrf_html_returns_markup_not_escaped_string() -> None:
    from flask import Flask, session

    app = Flask(__name__)
    app.secret_key = "test-secret"
    with app.test_request_context():
        session.clear()
        html = _generate_csrf_html()
        assert isinstance(html, Markup)
        assert str(html).startswith('<input type="hidden" name="csrf_token"')
        assert "&lt;input" not in str(html)
