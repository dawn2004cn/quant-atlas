"""Quant capability kernel API — no full app boot."""

from __future__ import annotations

from flask import Flask

from app.presentation.api.routes_v1_quant_capability import register_quant_capability_routes


def _client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    bp = __import__("flask").Blueprint("v1", __name__)
    register_quant_capability_routes(bp, ctx=None)
    app.register_blueprint(bp, url_prefix="/api/v1")
    return app.test_client()


def test_tearsheet_endpoint_returns_omega():
    client = _client()
    resp = client.post("/api/v1/quant/tearsheet", json={"returns": [0.02, -0.01, 0.03, -0.02]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "omega_ratio" in body["data"]
    assert body["data"]["omega_ratio"] > 0


def test_hrp_endpoint_rejects_empty():
    client = _client()
    resp = client.post("/api/v1/quant/hrp", json={"returns": {}})
    assert resp.status_code == 400


def test_factor_diagnostics_endpoint():
    client = _client()
    resp = client.post(
        "/api/v1/quant/factor-diagnostics",
        json={"factor": [1, 2, 3, 4, 5], "forward_returns": [0.01, 0.02, 0.03, 0.04, 0.05]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["rank_ic"] > 0.99
