"""System/User Service Adapters.

Adapters implement the System/User Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.system.ports import (
    AdminPort,
    SystemConfigPort,
    SystemHealthPort,
    TelemetryPort,
    UserProfilePort,
)


class SystemHealthAdapter(SystemHealthPort):
    """Adapts system health service to SystemHealthPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_health(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_health()
        return {"status": "ok", "services": {}}


class UserProfileAdapter(UserProfilePort):
    """Adapts user service to UserProfilePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_profile(self, user_id: int) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_profile(user_id)
        return {"user_id": user_id}

    def update_profile(self, user_id: int, profile: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.update_profile(user_id, profile)
        return {"updated": True}


class AdminAdapter(AdminPort):
    """Adapts admin service to AdminPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_dashboard(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_dashboard()
        return {"dashboard": {}}

    def get_audit_log(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        if self._service is not None:
            return self._service.get_audit_log(user_id, limit=limit)
        return []


class SystemConfigAdapter(SystemConfigPort):
    """Adapts config service to SystemConfigPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_config(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_config()
        return {"config": {}}

    def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.update_config(config)
        return {"updated": True}


class TelemetryAdapter(TelemetryPort):
    """Adapts telemetry service to TelemetryPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_telemetry(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_telemetry()
        return {"metrics": {}}


def create_system_user_ports(ctx: Any) -> dict[str, Any]:
    """Create all system/user ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    # System health is always available (no service dependency)
    ports["system_health"] = SystemHealthAdapter()

    if getattr(ctx, "user_service", None) is not None:
        ports["user_profile"] = UserProfileAdapter(ctx.user_service)

    if getattr(ctx, "rbac_service", None) is not None:
        ports["admin"] = AdminAdapter(ctx.rbac_service)

    if getattr(ctx, "config_service", None) is not None:
        ports["system_config"] = SystemConfigAdapter(ctx.config_service)

    if getattr(ctx, "decision_trace_service", None) is not None:
        ports["telemetry"] = TelemetryAdapter(ctx.decision_trace_service)

    return ports


__all__ = [
    "SystemHealthPort",
    "UserProfilePort",
    "AdminPort",
    "SystemConfigPort",
    "TelemetryPort",
    "SystemHealthAdapter",
    "UserProfileAdapter",
    "AdminAdapter",
    "SystemConfigAdapter",
    "TelemetryAdapter",
    "create_system_user_ports",
]
