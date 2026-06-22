"""System/User Service Ports (abstract interfaces).

Ports define the contracts that the System/User Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the System/User Service to be extracted as an independent microservice
in Phase 2F.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SystemHealthPort(ABC):
    """Port for system health operations."""

    @abstractmethod
    def get_health(self) -> dict[str, Any]:
        """Get system health status."""
        raise NotImplementedError


class UserProfilePort(ABC):
    """Port for user profile operations."""

    @abstractmethod
    def get_profile(self, user_id: int) -> dict[str, Any]:
        """Get user profile."""
        raise NotImplementedError

    @abstractmethod
    def update_profile(self, user_id: int, profile: dict[str, Any]) -> dict[str, Any]:
        """Update user profile."""
        raise NotImplementedError


class AdminPort(ABC):
    """Port for admin operations."""

    @abstractmethod
    def get_dashboard(self) -> dict[str, Any]:
        """Get admin dashboard data."""
        raise NotImplementedError

    @abstractmethod
    def get_audit_log(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get audit log for user."""
        raise NotImplementedError


class SystemConfigPort(ABC):
    """Port for system configuration operations."""

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """Get system configuration."""
        raise NotImplementedError

    @abstractmethod
    def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update system configuration."""
        raise NotImplementedError


class TelemetryPort(ABC):
    """Port for telemetry operations."""

    @abstractmethod
    def get_telemetry(self) -> dict[str, Any]:
        """Get system telemetry."""
        raise NotImplementedError
