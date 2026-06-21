"""Architecture gates for Phase C."""

from __future__ import annotations

from flask import Flask


def test_v1_responses_include_deprecation_headers():
    import werkzeug

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from app.presentation.api.v1_deprecation import register_v1_deprecation_headers

    app = Flask(__name__)

    @app.get("/api/v1/ping")
    def ping():
        return {"ok": True}

    @app.get("/api/v2/ping")
    def ping_v2():
        return {"ok": True}

    register_v1_deprecation_headers(app)

    with app.test_client() as client:
        v1 = client.get("/api/v1/ping")
        assert v1.headers.get("Deprecation") == "true"
        assert v1.headers.get("Sunset") == "2026-12-31"
        assert 'rel="successor-version"' in (v1.headers.get("Link") or "")
        assert v1.headers.get("X-API-Version") == "v1"

        v2 = client.get("/api/v2/ping")
        assert v2.headers.get("Deprecation") is None


def test_cross_module_import_baseline_not_exceeded():
    from scripts.check_module_cross_imports import BASELINE, count_cross_imports

    current = count_cross_imports()
    for pair, baseline in BASELINE.items():
        assert current.get(pair, 0) <= baseline, (
            f"cross-import {pair[0]} -> {pair[1]} increased: "
            f"{current.get(pair, 0)} > {baseline}"
        )
