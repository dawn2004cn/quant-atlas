"""Centralized health check implementations for all context modules."""

from __future__ import annotations

from typing import Any


def module_health_check(module_name: str, required_infra: list[str] | None = None) -> dict[str, Any]:
    """Generic health check for a context module.

    Args:
        module_name: The module name (e.g. "ai_agent", "market_data")
        required_infra: List of required infrastructure services ("mysql", "redis")

    Returns:
        Dict with status "ok"|"degraded"|"down" and detail.
    """
    infra_ok = True
    infra_checks = []

    if required_infra and "mysql" in required_infra:
        try:
            from app.infrastructure.database.connection import is_db_connected
            if callable(is_db_connected):
                db_ok = is_db_connected()
                infra_checks.append({"infra": "mysql", "ok": db_ok})
                if not db_ok:
                    infra_ok = False
        except Exception as e:
            infra_checks.append({"infra": "mysql", "ok": False, "error": str(e)})
            infra_ok = False

    if required_infra and "redis" in required_infra:
        try:
            import redis

            from app.config.settings import get_settings

            s = get_settings()
            redis_url = s.celery.broker_url or ""
            r = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            r.close()
            infra_checks.append({"infra": "redis", "ok": True})
        except Exception as e:
            infra_checks.append({"infra": "redis", "ok": False, "error": str(e)})
            infra_ok = False

    if required_infra and "openbb" in required_infra:
        try:
            from openbb import obb
            _ = obb
            infra_checks.append({"infra": "openbb", "ok": True})
        except Exception as e:
            infra_checks.append({"infra": "openbb", "ok": False, "error": str(e)})
            infra_ok = False

    status = "ok" if infra_ok else "degraded"
    return {
        "status": status,
        "module": module_name,
        "detail": {"infrastructure": infra_checks},
    }
