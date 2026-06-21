"""Background services configuration."""

from __future__ import annotations

from typing import Any


def resolve_background_policy(settings: Any = None) -> dict[str, Any]:
    """Resolve background services policy based on settings.

    Returns a dict describing which background services should run
    and how (celery tasks vs in-process threads).
    """
    if settings is None:
        return {
            "enabled": False,
            "services": [],
        }

    enable_scanner = getattr(settings, "enable_background_scanner", False)
    enable_basic_data = getattr(settings, "enable_basic_data_scheduler", False)
    services = []
    if enable_scanner:
        services.append("scanner")
    if enable_basic_data:
        services.append("basic_data_scheduler")

    return {
        "enabled": bool(services),
        "services": services,
    }


def start_background_services(settings: Any = None, services: Any = None, providers: Any = None) -> None:
    """Start background services."""
    pass

