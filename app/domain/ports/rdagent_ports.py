from __future__ import annotations
"""Ports for RD-Agent job store, artifact registry, and submission validation."""

from pathlib import Path
from typing import Any, Protocol


class RDAgentJobStorePort(Protocol):
    def create(self, *, params_summary: dict[str, Any]) -> str:
        ...

    def get(self, run_id: str) -> dict[str, Any] | None:
        ...

    def update(self, job_id: str, **kwargs: Any) -> None:
        ...


class RDAgentArtifactRegistryPort(Protocol):
    def get_run_bundle(self, run_id: str) -> dict[str, Any] | None:
        ...

    def list_registry_index(self, *, limit: int = 100) -> list[dict[str, Any]]:
        ...


class RDAgentValidationPort(Protocol):
    def validate_submission(self, body: dict[str, Any], *, base_dir: Path | None = None) -> None:
        ...
