from __future__ import annotations
"""Swarm Preset Repository for dynamic configurations."""


import json
from pathlib import Path
from typing import Any

from app.infrastructure.agent.swarm.models import SwarmAgentSpec, SwarmTask

class PresetRepository:
    """Repository for managing Swarm presets in the database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        # Using a simple JSON-based repo as a proxy for DB access for now
        self.db_path.mkdir(parents=True, exist_ok=True)

    def save_preset(self, name: str, config: dict[str, Any]) -> None:
        path = self.db_path / f"{name}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def get_preset(self, name: str) -> dict[str, Any] | None:
        path = self.db_path / f"{name}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_presets(self) -> list[str]:
        return [p.stem for p in self.db_path.glob("*.json")]
