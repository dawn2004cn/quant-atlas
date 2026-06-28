from __future__ import annotations

import gzip
import io

from flask import Flask, Response, request


def init_response_optimization(app: Flask) -> None:
    """Enable response compression and positive caching headers."""

    @app.after_request
    def compress_response(response: Response) -> Response:
        """Gzip-compress JSON responses larger than 1KB when client supports it."""
        if _should_compress(response):
            response = _gzip_response(response)
        return response

    @app.after_request
    def add_cache_headers(response: Response) -> Response:
        """Set positive Cache-Control for safe-to-cache responses."""
        if _is_cacheable(response):
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "public, max-age=300"
        return response


def _should_compress(response: Response) -> bool:
    if response.status_code >= 300:
        return False
    if "gzip" not in request.headers.get("Accept-Encoding", ""):
        return False
    content_type = response.content_type or ""
    if not content_type.startswith(("application/json", "text/", "application/javascript")):
        return False
    if response.content_length and response.content_length < 1024:
        return False
    return True


def _gzip_response(response: Response) -> Response:
    content = response.get_data()
    buf = io.BytesIO()
    with gzip.GzipFile(mode="wb", fileobj=buf) as gz:
        gz.write(content)
    compressed = buf.getvalue()
    if len(compressed) < len(content):
        response.set_data(compressed)
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed))
    return response


def _is_cacheable(response: Response) -> bool:
    if response.status_code not in {200, 203, 204, 301, 404}:
        return False
    content_type = response.content_type or ""
    if not content_type.startswith(("application/json", "text/", "application/javascript")):
        return False
    if response.headers.get("Cache-Control") in ("no-cache", "no-store", "private"):
        return False
    if request.method not in ("GET", "HEAD"):
        return False
    return True
