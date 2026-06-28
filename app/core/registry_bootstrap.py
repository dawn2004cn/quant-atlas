"""Bootstrap bridge for the service registry.

Provides ``configure_service_registry``, ``wire_from_registry``,
and ``rewire_infra_dependent_services`` — the DI wiring entry points
used during application bootstrap.

Uses ``TypedServiceRegistry`` internally.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.typed_registry import TypedServiceRegistry

logger = logging.getLogger(__name__)

_registry_instance: TypedServiceRegistry | None = None


def configure_service_registry(config: dict[str, Any] | None = None) -> TypedServiceRegistry:
    """Create or replace the bootstrap TypedServiceRegistry with config."""
    global _registry_instance
    from app.bootstrap_components.service_loader import preload_service_modules
    preload_service_modules()
    _registry_instance = TypedServiceRegistry(config=config or {})
    return _registry_instance


def _get_bootstrap_registry() -> TypedServiceRegistry | None:
    """Return the current bootstrap TypedServiceRegistry singleton."""
    return _registry_instance


def wire_from_registry(services: Any) -> None:
    """Resolve all registered service instances into *services* bundle."""
    reg = _get_bootstrap_registry()
    if reg is None:
        return
    for name in list(reg._config.keys()):
        if getattr(services, name, None) is not None:
            continue
        try:
            instance = reg.get(name)
            if instance is not None:
                setattr(services, name, instance)
        except Exception as exc:
            logger.debug("Could not wire %s: %s", name, exc)


def rewire_infra_dependent_services(services: Any) -> None:
    """Re-resolve infrastructure-dependent services."""
    wire_from_registry(services)
