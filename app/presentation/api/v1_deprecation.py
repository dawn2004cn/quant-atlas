"""Attach deprecation headers to legacy /api/v1 responses."""

from __future__ import annotations

from flask import Flask, request

# RFC 8594 / common API sunset practice — v2 is the successor surface.
V1_SUNSET_DATE = "2026-12-31"
V2_PREFIX = "/api/v2"


def register_v1_deprecation_headers(app: Flask) -> None:
    """Mark all v1 JSON API responses as deprecated in favor of v2."""

    @app.after_request
    def _v1_deprecation_headers(response):
        if not request.path.startswith("/api/v1/"):
            return response
        response.headers.setdefault("Deprecation", "true")
        response.headers.setdefault("Sunset", V1_SUNSET_DATE)
        response.headers.setdefault(
            "Link",
            f'<{V2_PREFIX}>; rel="successor-version"',
        )
        response.headers.setdefault("X-API-Version", "v1")
        return response
