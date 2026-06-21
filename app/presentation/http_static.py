from __future__ import annotations
"""Helpers for static asset HTTP handling."""


from flask import request


def is_static_asset_request() -> bool:
    """True when the request targets Flask's /static/ endpoint."""
    return request.path.startswith("/static/")
