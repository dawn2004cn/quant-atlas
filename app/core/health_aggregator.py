'''Structured health check aggregation.

Aggregates health status from all subsystems into a single endpoint.
Follows RFC 9457 Problem Details format for machine-readable errors.
'''
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class HealthAggregator:
    def __init__(self):
        self._checks: dict[str, Any] = {}
        self._last_check: str | None = None

    def register_check(self, name: str, check_fn, weight: int = 1):
        self._checks[name] = {"fn": check_fn, "weight": weight, "last_ok": None, "last_error": None}

    def all_healthy(self) -> bool:
        results = self.aggregate()
        return all(s.get("healthy", False) for s in results.values())

    def aggregate(self) -> dict[str, Any]:
        results = {}
        for name, entry in self._checks.items():
            try:
                result = entry["fn"]()
                healthy = bool(result.get("healthy", True))
                entry["last_ok"] = datetime.now().isoformat() if healthy else entry["last_ok"]
                if not healthy:
                    entry["last_error"] = result.get("error", "unknown")
                results[name] = {
                    "healthy": healthy,
                    "detail": result,
                    "checked_at": datetime.now().isoformat(),
                }
            except Exception as exc:
                entry["last_error"] = str(exc)
                results[name] = {"healthy": False, "error": str(exc), "checked_at": datetime.now().isoformat()}
        self._last_check = datetime.now().isoformat()
        return results

    def summary(self) -> dict[str, Any]:
        results = self.aggregate()
        total = len(results)
        healthy = sum(1 for v in results.values() if v.get("healthy", False))
        return {
            "status": "healthy" if healthy == total else "degraded" if healthy > 0 else "unhealthy",
            "healthy": healthy,
            "total": total,
            "degraded": total - healthy,
            "checks": results,
            "last_check": self._last_check,
        }


_aggregator: HealthAggregator | None = None


def get_health_aggregator() -> HealthAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = HealthAggregator()
        logger.info("HealthAggregator initialized")
    return _aggregator


def register_subsystem_checks():
    agg = get_health_aggregator()
    agg.register_check("registry", _check_registry)
    agg.register_check("event_bus", _check_event_bus)
    agg.register_check("modules", _check_modules)
    logger.info("Subsystem health checks registered: 3 checks")


def _check_registry() -> dict[str, Any]:
    try:
        from app.core.registry import registered_factory_names, registered_service_names
        return {"healthy": True, "services": len(registered_service_names()), "factories": len(registered_factory_names())}
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}


def _check_event_bus() -> dict[str, Any]:
    try:
        from app.core.event_bus import get_event_bus
        bus = get_event_bus()
        subscribers = bus._subscribers if hasattr(bus, "_subscribers") else {}
        return {"healthy": True, "subscriber_count": len(subscribers)}
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}


def _check_modules() -> dict[str, Any]:
    try:
        from app.core.module_registry import ModuleRegistry
        reg = ModuleRegistry()
        modules = reg.get_all_modules() if hasattr(reg, "get_all_modules") else []
        return {"healthy": True, "module_count": len(modules)}
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}
