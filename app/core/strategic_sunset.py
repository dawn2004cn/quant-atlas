"""P3 strategic feature sunset gates (AUDIT_REPORT1 §八).

Disabled by default. Set ``FEATURE_<NAME>=1`` in the environment to re-enable a
capability during development or for legacy deployments.
"""

from __future__ import annotations

from app.core.runtime_config import get_runtime_bool

# Env keys → audit bucket
_FEATURE_ENV: dict[str, str] = {
    "war_room": "FEATURE_WAR_ROOM",
    "alpha_marketplace": "FEATURE_ALPHA_MARKETPLACE",
    "decision_theater": "FEATURE_DECISION_THEATER",
    "swarm_topology": "FEATURE_SWARM_TOPOLOGY",
    "federated_mesh": "FEATURE_FEDERATED_MESH",
}

_FEATURE_LABELS: dict[str, str] = {
    "war_room": "War Room / Hyper 模拟器",
    "alpha_marketplace": "Alpha 因子市场 / ZK 治理",
    "decision_theater": "决策剧场 (3D / 回溯)",
    "swarm_topology": "Swarm 拓扑设计器",
    "federated_mesh": "联邦 Mesh / 集群",
}


def feature_enabled(feature: str) -> bool:
    """Return True when the strategic feature is explicitly enabled."""
    env_key = _FEATURE_ENV.get(feature)
    if not env_key:
        return False
    return get_runtime_bool(env_key, False)


def feature_label(feature: str) -> str:
    return _FEATURE_LABELS.get(feature, feature)


def jinja_feature_flags() -> dict[str, bool]:
    """Template context: ``feature_war_room``, etc."""
    return {f"feature_{name}": feature_enabled(name) for name in _FEATURE_ENV}


def feature_env_key(feature: str) -> str:
    return _FEATURE_ENV.get(feature, f"FEATURE_{feature.upper()}")


def api_path_sunset_feature(path: str) -> str | None:
    """Map ``/api/v1/...`` path to a sunset feature id, or None if allowed."""
    p = path.rstrip("/") or "/"
    if p.startswith("/api/v1"):
        p = p[len("/api/v1") :] or "/"

    rules: tuple[tuple[str, str], ...] = (
        ("/simulation/war-room", "war_room"),
        ("/simulation/hyper", "war_room"),
        ("/alpha/marketplace", "alpha_marketplace"),
        ("/alpha/governance", "alpha_marketplace"),
        ("/alpha/wallet", "alpha_marketplace"),
        ("/alpha/tokens", "alpha_marketplace"),
        ("/panorama/decision-3d", "decision_theater"),
        ("/panorama/evolution-tournament", "alpha_marketplace"),
        ("/decision-replay", "decision_theater"),
        ("/decision-theater", "decision_theater"),
        ("/mesh", "federated_mesh"),
        ("/wisdom-mesh", "federated_mesh"),
        ("/cognitive-mesh", "federated_mesh"),
        ("/user-tiers/institution/federated", "federated_mesh"),
        ("/swarm/topology", "swarm_topology"),
    )
    for prefix, feature in rules:
        if p == prefix or p.startswith(prefix + "/"):
            return feature
    return None
