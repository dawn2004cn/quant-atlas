from __future__ import annotations
"""Dependency injection container shim.

Deprecated: the application now uses ``app.core.registry`` (TypedServiceRegistry)
for all service wiring. This module is retained only as a backward-compatible
no-op for legacy scripts that import ``Container`` directly.

If you see this module being imported, remove the import and use the registry:
    from app.core.registry import get_registry
    reg = get_registry()
    svc = reg.get("service_name")
"""

from typing import Any


class _LegacyContainerShim:
    """Minimal shim replacing the old dependency_injector Container."""

    def __getattr__(self, name: str) -> Any:
        from app.core.registry import get_registry
        reg = get_registry()
        try:
            return reg.get(name)
        except Exception:
            raise AttributeError(
                f"Container shim: service '{name}' not found in registry. "
                "Use get_registry().get('{name}') directly."
            )


container = _LegacyContainerShim()
Container = _LegacyContainerShim
