from __future__ import annotations
"""Infrastructure adapters for RD-Agent ports."""

from pathlib import Path
from typing import Any

from app.domain.ports.rdagent_ports import (
    RDAgentArtifactRegistryPort,
    RDAgentJobStorePort,
    RDAgentValidationPort,
)
from app.infrastructure.rdagent.artifact_registry import RDAgentArtifactRegistry
from app.infrastructure.rdagent.job_store import RDAgentJobStore
from app.infrastructure.rdagent.submission_validate import validate_rd_factor_submission


class RDAgentJobStorePortAdapter(RDAgentJobStorePort):
    def __init__(self, base_dir: Path) -> None:
        self._store = RDAgentJobStore(base_dir)

    def create(self, *, params_summary: dict[str, Any]) -> str:
        return self._store.create(params_summary=params_summary)

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self._store.get(run_id)

    def update(self, job_id: str, **kwargs: Any) -> None:
        self._store.update(job_id, **kwargs)


class RDAgentArtifactRegistryPortAdapter(RDAgentArtifactRegistryPort):
    def __init__(self, base_dir: Path) -> None:
        self._registry = RDAgentArtifactRegistry(base_dir)

    def get_run_bundle(self, run_id: str) -> dict[str, Any] | None:
        return self._registry.get_run_bundle(run_id)

    def list_registry_index(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._registry.list_registry_index(limit=limit)


class RDAgentValidationPortAdapter(RDAgentValidationPort):
    def validate_submission(self, body: dict[str, Any], *, base_dir: Path | None = None) -> None:
        validate_rd_factor_submission(body, base_dir=base_dir)
