"""P3 strategic sunset gate tests."""

from __future__ import annotations

from app.core.strategic_sunset import (
    api_path_sunset_feature,
    feature_enabled,
)


def test_features_disabled_by_default(monkeypatch):
    for key in (
        "FEATURE_WAR_ROOM",
        "FEATURE_ALPHA_MARKETPLACE",
        "FEATURE_DECISION_THEATER",
        "FEATURE_SWARM_TOPOLOGY",
        "FEATURE_FEDERATED_MESH",
    ):
        monkeypatch.delenv(key, raising=False)
    assert feature_enabled("war_room") is False
    assert feature_enabled("alpha_marketplace") is False


def test_feature_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("FEATURE_WAR_ROOM", "1")
    assert feature_enabled("war_room") is True


def test_api_path_mapping():
    assert api_path_sunset_feature("/api/v1/simulation/war-room/scenarios") == "war_room"
    assert api_path_sunset_feature("/api/v1/alpha/marketplace/listings") == "alpha_marketplace"
    assert api_path_sunset_feature("/api/v1/alpha/tokens/list") == "alpha_marketplace"
    assert api_path_sunset_feature("/api/v1/panorama/decision-3d") == "decision_theater"
    assert api_path_sunset_feature("/api/v1/decision-theater/space") == "decision_theater"
    assert api_path_sunset_feature("/api/v1/cognitive-mesh/status") == "federated_mesh"
    assert (
        api_path_sunset_feature("/api/v1/user-tiers/institution/federated/nodes")
        == "federated_mesh"
    )
    assert api_path_sunset_feature("/api/v1/market/panorama") is None
