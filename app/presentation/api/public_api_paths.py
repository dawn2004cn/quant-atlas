"""Intentionally unauthenticated /api/v1 paths (probes & retail compliance copy).

These routes are registered **without** ``@login_required``. They must remain
read-only and must not expose user-specific or market-moving data.

Keep in sync with:
- ``routes_v1_compliance.py`` (manifest)
- ``routes_v1_system_health.py`` (health probes)
- ``tests/api/test_public_api_contract.py``
"""

from __future__ import annotations

# Exact paths (no trailing slash) allowed for anonymous GET.
PUBLIC_API_V1_GET_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/compliance/manifest",
        "/api/v1/health",
        "/api/v1/system/health",
    }
)


def normalize_api_path(path: str) -> str:
    """Strip query string and trailing slash for comparison."""
    base = (path or "").split("?", 1)[0].strip()
    if base != "/" and base.endswith("/"):
        base = base.rstrip("/")
    return base or "/"


def is_public_api_v1_path(path: str, *, method: str = "GET") -> bool:
    """Return True when *path* is an intentionally public API v1 endpoint."""
    if method.upper() not in ("GET", "HEAD"):
        return False
    return normalize_api_path(path) in PUBLIC_API_V1_GET_PATHS


__all__ = [
    "PUBLIC_API_V1_GET_PATHS",
    "is_public_api_v1_path",
    "normalize_api_path",
]
