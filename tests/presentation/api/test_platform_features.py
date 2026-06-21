"""Platform strategic-features API tests."""

from __future__ import annotations


def test_strategic_features_endpoint_defaults(client, monkeypatch):
    for key in (
        "FEATURE_WAR_ROOM",
        "FEATURE_ALPHA_MARKETPLACE",
        "FEATURE_DECISION_THEATER",
        "FEATURE_SWARM_TOPOLOGY",
        "FEATURE_FEDERATED_MESH",
    ):
        monkeypatch.delenv(key, raising=False)

    res = client.get("/api/v1/platform/strategic-features")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    data = body["data"]
    assert data["feature_alpha_marketplace"] is False
    assert data["feature_federated_mesh"] is False


def test_strategic_features_endpoint_when_enabled(client, monkeypatch):
    monkeypatch.setenv("FEATURE_ALPHA_MARKETPLACE", "1")
    res = client.get("/api/v1/platform/strategic-features")
    assert res.status_code == 200
    assert res.get_json()["data"]["feature_alpha_marketplace"] is True
