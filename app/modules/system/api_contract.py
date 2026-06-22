"""System/User Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the System/User Service,
which will be extracted as an independent microservice in Phase 2F.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/system/*)
"""

from __future__ import annotations

from typing import Any


class SystemUserServicePort:
    """Port (interface) for system and user operations."""

    def get_system_health(self) -> dict[str, Any]:
        """Get system health status."""
        raise NotImplementedError

    def get_user_profile(self, user_id: int) -> dict[str, Any]:
        """Get user profile."""
        raise NotImplementedError

    def update_user_profile(self, user_id: int, profile: dict[str, Any]) -> dict[str, Any]:
        """Update user profile."""
        raise NotImplementedError

    def get_admin_dashboard(self) -> dict[str, Any]:
        """Get admin dashboard data."""
        raise NotImplementedError

    def get_system_config(self) -> dict[str, Any]:
        """Get system configuration."""
        raise NotImplementedError

    def update_system_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update system configuration."""
        raise NotImplementedError

    def get_audit_log(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get audit log for user."""
        raise NotImplementedError

    def get_telemetry(self) -> dict[str, Any]:
        """Get system telemetry."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "system_user",
    "version": "v1",
    "base_path": "/api/v1/system",
    "endpoints": [
        {
            "method": "GET",
            "path": "/health",
            "summary": "Get system health",
            "params": [],
            "response": {"status": "str", "services": {}},
            "latency_target_ms": 100,
        },
        {
            "method": "GET",
            "path": "/user/{user_id}/profile",
            "summary": "Get user profile",
            "params": ["user_id (path)"],
            "response": {"profile": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "PUT",
            "path": "/user/{user_id}/profile",
            "summary": "Update user profile",
            "params": ["user_id (path)", "profile (body)"],
            "response": {"updated": "bool"},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/admin/dashboard",
            "summary": "Get admin dashboard",
            "params": [],
            "response": {"dashboard": {}},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/config",
            "summary": "Get system config",
            "params": [],
            "response": {"config": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "PUT",
            "path": "/config",
            "summary": "Update system config",
            "params": ["config (body)"],
            "response": {"updated": "bool"},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/audit/{user_id}",
            "summary": "Get audit log",
            "params": ["user_id (path)", "limit (query)"],
            "response": [{"action": "str", "timestamp": "str"}],
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/telemetry",
            "summary": "Get system telemetry",
            "params": [],
            "response": {"metrics": {}},
            "latency_target_ms": 200,
        },
    ],
}


def get_system_user_api_contract() -> dict[str, Any]:
    """Return the System/User Service API contract."""
    return API_CONTRACT
