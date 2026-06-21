"""Security headers middleware for Flask applications.

Centralizes CSP, HSTS, and other security headers to keep bootstrap.py
focused on dependency wiring rather than HTTP header management.

CSP uses a per-request nonce for inline **scripts**.  Templates that emit
inline ``<script>`` tags MUST include ``nonce="{{ csp_nonce() }}"``.

Phase 2 Scope (deferred): Remove 'unsafe-inline' from style-src.
- Audit found 80+ templates with hundreds of inline ``style=`` attributes
- Strategy: consolidate repeated inline styles into CSS classes
- Risk: broken UI if migration is incomplete; requires end-to-end visual QA
- Estimated effort: 2-3 sessions
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import urlparse

from flask import Flask, Response, g


def _generate_csp_nonce() -> str:
    """Generate a cryptographically random 32-character hex nonce."""
    return secrets.token_hex(16)


def _allowed_connect_origins() -> list[str]:
    """Build connect-src origins from runtime config, not hardcoded."""
    from app.core.runtime_config import get_runtime
    origins: list[str] = ["'self'", "http://localhost:*", "https://localhost:*"]
    raw = (get_runtime("ALLOWED_CONNECT_ORIGINS") or "").strip()
    if raw:
        for url in raw.split(","):
            url = url.strip()
            if url:
                parsed = urlparse(url)
                scheme = parsed.scheme or "https"
                host = parsed.hostname or parsed.netloc
                if host:
                    port = f":{parsed.port}" if parsed.port else ""
                    origins.append(f"{scheme}://{host}{port}")
    return origins


def _sanitize_sql_statement(stmt: str) -> str:
    """Strip SQL comments and truncate for safe logging."""
    cleaned = re.sub(r"--.*$", "", stmt, flags=re.MULTILINE).strip()
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "..."
    return cleaned


def configure_security_headers(app: Flask, *, debug: bool = False) -> None:
    """Attach security headers to every response.

    Args:
        app: Flask application instance.
        debug: If True, skips HSTS (HTTP Strict Transport Security).
    """

    @app.before_request
    def _generate_nonce() -> None:
        """Generate a per-request CSP nonce before any view runs."""
        g.csp_nonce = _generate_csp_nonce()

    @app.after_request
    def _add_security_headers(response: Response) -> Response:
        nonce = getattr(g, "csp_nonce", "")
        nonce_src = f"'nonce-{nonce}'" if nonce else ""

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        if not debug:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains; preload"

        script_nonce = f" {nonce_src}" if nonce_src else ""
        connect_origins = " ".join(_allowed_connect_origins())

        csp_parts = [
            "default-src 'self';",
            f"script-src 'self'{script_nonce} https://cdn.jsdelivr.net https://cdn.bootcdn.net;",
            # Phase 2: Remove 'unsafe-inline' — requires 80+ template audit
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
            "https://cdn.jsdelivr.net https://cdn.bootcdn.net;",
            "font-src 'self' https://fonts.gstatic.com "
            "https://cdn.jsdelivr.net https://cdn.bootcdn.net data:;",
            "img-src 'self' data: https:;",
            f"connect-src {connect_origins};",
            "frame-ancestors 'self';",
        ]
        response.headers["Content-Security-Policy"] = " ".join(csp_parts)
        return response


def csp_nonce() -> str:
    """Template global: return the current request's CSP nonce."""
    return getattr(g, "csp_nonce", "")
