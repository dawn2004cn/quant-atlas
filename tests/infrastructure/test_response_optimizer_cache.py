from __future__ import annotations

from flask import Flask, jsonify

from app.infrastructure.response_optimizer import init_response_optimization


def _make_app() -> Flask:
    app = Flask(__name__)
    init_response_optimization(app)

    @app.get("/api/v1/quotes/demo")
    def quotes_demo():
        return jsonify({"ok": True, "data": {"price": 1}})

    @app.get("/api/v1/platform/strategic-features")
    def features():
        resp = jsonify({"ok": True, "data": {"feature_war_room": False}})
        resp.headers["Cache-Control"] = "private, max-age=600"
        return resp

    @app.get("/healthz-text")
    def health_text():
        return "ok", 200, {"Content-Type": "text/plain"}

    return app


def test_api_json_does_not_get_public_max_age_300() -> None:
    client = _make_app().test_client()
    resp = client.get("/api/v1/quotes/demo")
    assert resp.status_code == 200
    cc = resp.headers.get("Cache-Control", "")
    assert "public, max-age=300" not in cc


def test_strategic_features_keeps_private_cache_header() -> None:
    client = _make_app().test_client()
    resp = client.get("/api/v1/platform/strategic-features")
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "private, max-age=600"


def test_non_api_text_may_still_receive_positive_cache() -> None:
    client = _make_app().test_client()
    resp = client.get("/healthz-text")
    assert resp.status_code == 200
    # Non-API text/plain GET can still get the optimizer default when unset.
    assert resp.headers.get("Cache-Control") == "public, max-age=300"
