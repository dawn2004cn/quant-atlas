from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.agent_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.agent_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound agent/swarm infrastructure for application services."""

from collections.abc import Callable
from typing import Any

from app.domain.ports.agent_ports import ExpertSkillPort, SwarmOrchestratorPort

_create_swarm_orchestrator: Callable[[], SwarmOrchestratorPort] | None = None
_create_expert_skill: Callable[[], ExpertSkillPort] | None = None
_create_experiment_repository: Callable[[], Any] | None = None
_create_swarm_runtime: Callable[[], Any] | None = None
def bind_agent_infrastructure(
    *,
    swarm_orchestrator_factory: Callable[[], SwarmOrchestratorPort],
    expert_skill_factory: Callable[[], ExpertSkillPort],
    experiment_repository_factory: Callable[[], Any],
    swarm_runtime_factory: Callable[[], Any],
) -> None:
    global _create_swarm_orchestrator, _create_expert_skill
    global _create_experiment_repository, _create_swarm_runtime
    _create_swarm_orchestrator = swarm_orchestrator_factory
    _create_expert_skill = expert_skill_factory
    _create_experiment_repository = experiment_repository_factory
    _create_swarm_runtime = swarm_runtime_factory
def create_swarm_orchestrator_port() -> SwarmOrchestratorPort:
    if _create_swarm_orchestrator is None:
        raise RuntimeError("Agent infrastructure not configured; bootstrap must bind it")
    return _create_swarm_orchestrator()
def create_expert_skill_port() -> ExpertSkillPort:
    if _create_expert_skill is None:
        raise RuntimeError("Agent infrastructure not configured; bootstrap must bind it")
    return _create_expert_skill()
def create_default_experiment_repository() -> Any:
    if _create_experiment_repository is None:
        raise RuntimeError("Agent infrastructure not configured; bootstrap must bind it")
    return _create_experiment_repository()
def create_default_swarm_runtime() -> Any:
    if _create_swarm_runtime is None:
        raise RuntimeError("Agent infrastructure not configured; bootstrap must bind it")
    return _create_swarm_runtime()
