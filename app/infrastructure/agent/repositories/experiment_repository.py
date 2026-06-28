from __future__ import annotations
"""Experiment Repository implementation."""


import json
from pathlib import Path

from app.core.logger import get_logger
from app.domain.entities import Experiment

logger = get_logger(__name__)

class ExperimentRepository:
    """JSON-file based repository for Experiment entities."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, experiment: Experiment) -> None:
        path = self.storage_dir / f"{experiment.id}.json"

        # Optimistic Locking check
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if existing_data.get("version", 0) != experiment.version - 1:
                    raise Exception(f"Concurrency conflict: Experiment {experiment.id} has been modified.")

        with path.open("w", encoding="utf-8") as f:
            data = experiment.__dict__.copy()
            data['created_at'] = experiment.created_at.isoformat()
            json.dump(data, f, indent=2)

    def get(self, experiment_id: str) -> Experiment | None:
        path = self.storage_dir / f"{experiment_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return Experiment(**data)

    def list_all(self) -> list[Experiment]:
        experiments = []
        for path in self.storage_dir.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    # Add defensive defaults for missing fields
                    data.setdefault("version", 1)
                    data.setdefault("artifacts", {})
                    data.setdefault("metadata", {})
                    experiments.append(Experiment(**data))
                except Exception as e:
                    logger.warning(f"Skipping corrupt experiment file {path}: {e}")
        return experiments
