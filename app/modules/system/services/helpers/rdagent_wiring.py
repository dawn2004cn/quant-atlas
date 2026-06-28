"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.rdagent_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

from __future__ import annotations

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.rdagent_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound RD-Agent infrastructure for application services."""

from collections.abc import Callable
from pathlib import Path

from app.domain.ports.rdagent_ports import (
    RDAgentArtifactRegistryPort,
    RDAgentJobStorePort,
    RDAgentValidationPort,
)

_job_store_factory: Callable[[Path], RDAgentJobStorePort] | None = None
_artifact_registry_factory: Callable[[Path], RDAgentArtifactRegistryPort] | None = None
_validation: RDAgentValidationPort | None = None


def bind_rdagent_infrastructure(
    *,
    job_store_factory: Callable[[Path], RDAgentJobStorePort],
    artifact_registry_factory: Callable[[Path], RDAgentArtifactRegistryPort],
    validation: RDAgentValidationPort,
) -> None:
    global _job_store_factory, _artifact_registry_factory, _validation
    _job_store_factory = job_store_factory
    _artifact_registry_factory = artifact_registry_factory
    _validation = validation


def create_rdagent_job_store(base_dir: Path) -> RDAgentJobStorePort:
    if _job_store_factory is None:
        raise RuntimeError("RDAgent infrastructure not configured; bootstrap must bind it")
    return _job_store_factory(base_dir)


def create_rdagent_artifact_registry(base_dir: Path) -> RDAgentArtifactRegistryPort:
    if _artifact_registry_factory is None:
        raise RuntimeError("RDAgent infrastructure not configured; bootstrap must bind it")
    return _artifact_registry_factory(base_dir)


def get_rdagent_validation_port() -> RDAgentValidationPort:
    if _validation is None:
        raise RuntimeError("RDAgent validation not configured; bootstrap must bind it")
    return _validation
