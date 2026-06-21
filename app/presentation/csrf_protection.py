"""CSRF protection for Flask web forms and authenticated API routes.

Web forms (login, register, template POSTs) use full CSRF validation.
API routes (/api/*) that use @login_required also validate CSRF via
X-CSRF-Token / X-CSRFToken header. Public API routes (no login_required)
are exempt because browsers won't send cookies cross-origin with
application/json content-type.

Bearer JWT authenticated requests (no session cookie) are protected by
requiring an anti-forgery token in the X-JWT-CSRF-Token header for
state-changing methods (POST/PUT/DELETE/PATCH). This prevents CSRF attacks
against JWT-authenticated endpoints since JWT tokens are not sent automatically
by browsers like session cookies are.

Session-cookie authenticated requests already have CSRF protection via the
existing X-CSRF-Token mechanism (browsers send cookies cross-origin, so the
CSRF token in the cookie binds the request to the user's session).
"""

from __future__ import annotations

import logging
import secrets
from typing import Callable

from flask import Flask, request, session
from markupsafe import Markup, escape

logger = logging.getLogger(__name__)


def _csrf_token() -> str:
    """Get or create the CSRF token for the current session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def _generate_csrf_html() -> Markup:
    """Generate a hidden input for CSRF token embedding in forms."""
    token = escape(_csrf_token())
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')


def _has_active_session() -> bool:
    """Check if the current request has an active session (session-cookie auth)."""
    return "_fresh" in session or "_user_id" in session


def _has_jwt_auth() -> bool:
    """Check if the current request uses Bearer JWT authentication.

    Looks for the Authorization: Bearer <token> header, which indicates
    JWT-based authentication without session cookies.
    """
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer ") and len(auth_header) > 7


def _check_jwt_csrf_token() -> bool:
    """Validate CSRF token for Bearer JWT authenticated requests.

    JWT tokens are not sent automatically by browsers (unlike session cookies),
    so a standard CSRF token in a cookie wouldn't protect against cross-site
    request forgery. Instead, we require an anti-forgery token passed in the
    X-JWT-CSRF-Token header. This token should be generated server-side and
    embedded in the frontend application's state, then included with every
    state-changing request.
    """
    token = request.headers.get("X-JWT-CSRF-Token")
    if not token:
        return False
    # Compare against the session CSRF token (shared secret between
    # frontend and backend that the attacker cannot read cross-origin).
    expected = _csrf_token()
    return secrets.compare_digest(token, expected)


def _validate_csrf_token(app: Flask) -> bool:
    """Validate the CSRF token from request form/data/header."""
    # Skip validation for exempt methods
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return True

    # Skip static files
    if request.path.startswith("/static/"):
        return True

    # Skip OAuth callback endpoints only (GET-only, validated via state param)
    if request.method == "GET" and request.path in ("/auth/wechat/callback", "/auth/oauth/callback"):
        return True

    # API routes: validate CSRF for authenticated requests
    # - Session-cookie auth: existing X-CSRF-Token validation (browser sends cookies)
    # - Bearer JWT auth: X-JWT-CSRF-Token validation (JWT not auto-sent by browsers)
    # - Unauthenticated: exempt (no cookies to exploit)
    if request.path.startswith("/api/"):
        if _has_active_session():
            return _check_api_csrf_token()
        if _has_jwt_auth():
            return _check_jwt_csrf_token()
        return True

    # Web form routes: full CSRF validation
    return _check_web_csrf_token()


def _check_api_csrf_token() -> bool:
    """Check CSRF token for authenticated API requests.

    Validates X-CSRF-Token or X-CSRFToken header.
    Returns True if header is present and valid, or if no session exists.
    """
    token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
    if not token:
        return False
    expected = _csrf_token()
    return secrets.compare_digest(token, expected)


def _check_web_csrf_token() -> bool:
    """Full CSRF validation for web form submissions."""
    # Check header first (for AJAX/fetch requests to web routes)
    token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
    if token:
        expected = _csrf_token()
        return secrets.compare_digest(token, expected)

    # Check form data
    form_token = (
        request.form.get("csrf_token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
    )
    if not form_token:
        return False

    expected = _csrf_token()
    return secrets.compare_digest(form_token, expected)


def csrf_protect(app: Flask) -> None:
    """Attach CSRF protection to a Flask app.

    Protects:
    - Web-form POST/PUT/DELETE/PATCH requests with full CSRF validation.
    - Session-cookie authenticated API routes (via X-CSRF-Token header).
    - Bearer JWT authenticated API routes (via X-JWT-CSRF-Token header).
      Since JWT tokens are not auto-sent by browsers, this prevents CSRF
      attacks against JWT endpoints.
    - Unauthenticated API routes are exempt (no cookies to exploit).
    """
    @app.before_request
    def _csrf_before():
        if app.testing:
            return None
        endpoint = request.endpoint
        if endpoint:
            view = app.view_functions.get(endpoint)
            if view is not None and getattr(view, "_csrf_exempt", False):
                return None
        if not _validate_csrf_token(app):
            logger.warning("CSRF validation failed for %s %s", request.method, request.path)
            from flask import jsonify
            return jsonify({"error": "CSRF token missing or invalid"}), 403

    # Expose helpers in templates
    app.jinja_env.globals["csrf_token"] = _csrf_token
    app.jinja_env.globals["csrf_html"] = _generate_csrf_html


def with_csrf_exempt(f: Callable) -> Callable:
    """Decorator to exempt a specific route from CSRF (rarely needed)."""
    f._csrf_exempt = True  # type: ignore[attr-defined]
    return f
