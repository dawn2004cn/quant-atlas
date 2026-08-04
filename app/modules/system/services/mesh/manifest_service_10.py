"""Quant Atlas 10.0 unified manifest — aggregates optional mesh component status."""

from __future__ import annotations

from typing import Any, Callable

from app.core.logger import get_logger

logger = get_logger(__name__)

_COMPONENT_REGISTRY: dict[str, tuple[str, str]] = {
    "perception_resonance": ("perception_resonance_service", "get_stats"),
    "self_healing_execution": ("self_healing_execution_service", "get_manifest"),
    "evolution_arbiter": ("evolution_arbiter_service", "get_status"),
    "data_truth_guardian": ("data_truth_guardian_service", "get_manifest"),
    "wisdom_mesh": ("wisdom_mesh_service", "get_manifest"),
    "borderless_execution": ("borderless_execution_service", "get_manifest"),
    "hyper_simulator": ("hyper_simulator_service", "get_manifest"),
    "mesh_gateway": ("mesh_gateway_service", "get_manifest"),
}


class ManifestService10:
    """Surface 10.0 component availability without hard-failing when optional deps are missing."""

    def __init__(self, *, registry: Any | None = None) -> None:
        self._registry = registry

    def _resolve(self, service_name: str) -> Any | None:
        if self._registry is None:
            return None
        getter: Callable[[str], Any | None] | None = getattr(
            self._registry, "get_or_none", None
        )
        if callable(getter):
            return getter(service_name)
        return getattr(self._registry, service_name, None)

    def _probe(self, service_name: str, method_name: str) -> dict[str, Any]:
        svc = self._resolve(service_name)
        if svc is None:
            return {"available": False, "service": service_name}
        probe = getattr(svc, method_name, None)
        if not callable(probe):
            return {"available": True, "service": service_name, "status": "wired"}
        try:
            payload = probe()
            if isinstance(payload, dict):
                return {"available": True, "service": service_name, **payload}
            return {"available": True, "service": service_name, "status": payload}
        except Exception as exc:
            logger.warning("manifest probe %s.%s failed", service_name, method_name, exc_info=True)
            return {"available": True, "service": service_name, "error": str(exc)}

    def get_manifest(self) -> dict[str, Any]:
        components = {
            key: self._probe(service_name, method_name)
            for key, (service_name, method_name) in _COMPONENT_REGISTRY.items()
        }
        available_count = sum(1 for c in components.values() if c.get("available"))
        return {
            "ok": True,
            "version": "10.0",
            "components": components,
            "summary": {
                "total": len(components),
                "available": available_count,
                "degraded": len(components) - available_count,
            },
        }

    def get_component_detail(self, component_name: str) -> dict[str, Any]:
        key = component_name.strip().lower().replace("-", "_")
        if key not in _COMPONENT_REGISTRY:
            return {"ok": False, "error": "unknown_component", "component": component_name}
        service_name, method_name = _COMPONENT_REGISTRY[key]
        detail = self._probe(service_name, method_name)
        return {"ok": True, "component": key, **detail}


__all__ = ["ManifestService10"]
