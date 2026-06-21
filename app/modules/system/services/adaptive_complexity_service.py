"""Adaptive Complexity Mesh — Phase 18.4.
Dynamic compute routing based on user Archetype + auto-evolving UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# Compute depth levels per archetype
ARCHETYPE_COMPUTE_MAP = {
    "novice": {
        "rust_ops": True,           # fast Rust core
        "gnn_scan": False,          # no deep GNN
        "temporal_kg": False,       # no temporal pattern matching
        "neural_mesh": False,       # no feature crowding
        "immune_sim": False,        # no immune simulation
        "max_concurrent_agents": 1,
        "cache_ttl_seconds": 300,
    },
    "day_trader": {
        "rust_ops": True,
        "gnn_scan": False,
        "temporal_kg": True,
        "neural_mesh": False,
        "immune_sim": False,
        "max_concurrent_agents": 3,
        "cache_ttl_seconds": 60,
    },
    "strategist": {
        "rust_ops": True,
        "gnn_scan": True,
        "temporal_kg": True,
        "neural_mesh": True,
        "immune_sim": True,
        "max_concurrent_agents": 5,
        "cache_ttl_seconds": 30,
    },
}


@dataclass
class ComplexityProfile:
    """User's current complexity profile."""
    user_id: int
    archetype: str = "novice"
    compute_depth: dict = field(default_factory=dict)
    ui_layers: list[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptiveComplexityService:
    """Routes compute depth and UI layers based on user archetype."""

    def __init__(self):
        self._profiles: dict[int, ComplexityProfile] = {}

    def get_profile(self, user_id: int, archetype: str | None = None) -> ComplexityProfile:
        """Get or create complexity profile for user."""
        if user_id in self._profiles:
            return self._profiles[user_id]

        archetype = archetype or "novice"
        config = ARCHETYPE_COMPUTE_MAP.get(archetype, ARCHETYPE_COMPUTE_MAP["novice"])
        ui_layers = self._archetype_ui_layers(archetype)

        profile = ComplexityProfile(
            user_id=user_id,
            archetype=archetype,
            compute_depth=dict(config),
            ui_layers=ui_layers,
        )
        self._profiles[user_id] = profile
        return profile

    def evolve_archetype(self, user_id: int, new_archetype: str) -> ComplexityProfile:
        """Evolve user to a new archetype, unlocking more features."""
        profile = self.get_profile(user_id)
        profile.archetype = new_archetype
        config = ARCHETYPE_COMPUTE_MAP.get(new_archetype, ARCHETYPE_COMPUTE_MAP["novice"])
        profile.compute_depth = dict(config)
        profile.ui_layers = self._archetype_ui_layers(new_archetype)
        profile.last_updated = datetime.now(timezone.utc).isoformat()
        logger.info("User %d evolved to archetype %s", user_id, new_archetype)
        return profile

    def should_run_gnn(self, user_id: int) -> bool:
        """Check if user should get GNN feature scan."""
        profile = self.get_profile(user_id)
        return profile.compute_depth.get("gnn_scan", False)

    def should_run_immune(self, user_id: int) -> bool:
        """Check if user should get immune simulation."""
        profile = self.get_profile(user_id)
        return profile.compute_depth.get("immune_sim", False)

    def max_agents(self, user_id: int) -> int:
        """Get max concurrent agents for user."""
        profile = self.get_profile(user_id)
        return profile.compute_depth.get("max_concurrent_agents", 1)

    def get_ui_layers(self, user_id: int) -> list[str]:
        """Get enabled UI layers for user."""
        profile = self.get_profile(user_id)
        return profile.ui_layers

    def _archetype_ui_layers(self, archetype: str) -> list[str]:
        """Map archetype to enabled UI layers."""
        base = ["kline", "search_bar"]
        if archetype == "novice":
            return base + ["simple_indicators"]
        if archetype == "day_trader":
            return base + ["volume", "indicators", "level2", "hot_sectors", "temporal_kg"]
        if archetype == "strategist":
            return base + ["volume", "indicators", "level2", "hot_sectors",
                          "temporal_kg", "neural_mesh", "immune_sim",
                          "factor_ic", "alpha_search", "3d_resonance"]
        return base
