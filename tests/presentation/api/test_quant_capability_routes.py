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


def test_evaluate_expression_endpoint():
    client = _client()
    resp = client.post(
        "/api/v1/quant/evaluate-expression",
        json={"expression": "add(x0,x1)", "features": {"x0": [1, 2], "x1": [3, 4]}},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["values"] == [4, 6]


def test_evaluate_expression_rejects_eval():
    client = _client()
    resp = client.post(
        "/api/v1/quant/evaluate-expression",
        json={"expression": "eval(x0)", "features": {"x0": [1]}},
    )
    assert resp.status_code == 400


def test_ic_decay_endpoint():
    client = _client()
    resp = client.post(
        "/api/v1/quant/ic-decay",
        json={"expression": "x0", "returns": [0.01, -0.02] * 20, "windows": [20]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["ic_by_window"]["20"] > 0.99


def test_hyperopt_endpoint():
    client = _client()
    resp = client.post(
        "/api/v1/quant/hyperopt",
        json={
            "prices": [100 + i for i in range(80)],
            "param_grid": {"fast_ma": [5], "slow_ma": [20]},
            "strategy": "trend_following_basic",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["n_trials"] == 1
    assert body["best"]["params"]["fast_ma"] == 5
