"""OpenAPI spec builder using apispec + FlaskPlugin.

Generates OpenAPI 3.0 spec from Flask routes with docstring annotations.
"""
from __future__ import annotations

from typing import Any

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin


def build_spec(app: Any) -> APISpec:
    """Build OpenAPI spec from Flask app routes."""
    spec = APISpec(
        title="QuantAtlas API",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[FlaskPlugin()],
    )

    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            endpoint = rule.endpoint
            if endpoint == "static":
                continue
            view = app.view_functions.get(endpoint)
            if view is None:
                continue
            # Only include endpoints that have been marked for OpenAPI
            # (check for docstring with YAML front matter or _apispec_path attribute)
            if getattr(view, "_apispec_path", False) or _has_api_docs(view):
                try:
                    spec.path(view=view)
                except Exception:
                    pass

    return spec


def _has_api_docs(view) -> bool:
    """Check if view function has OpenAPI docstring."""
    doc = getattr(view, "__doc__", None) or ""
    return "---" in doc and ("get:" in doc or "post:" in doc or "put:" in doc or "delete:" in doc)
