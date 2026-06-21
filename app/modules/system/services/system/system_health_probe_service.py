from __future__ import annotations

"""System component health probes via application ports."""

from typing import Any

from app.config import get_settings


class SystemHealthProbeService:
    """Lightweight probes for system health endpoints."""

    @staticmethod
    def probe_mysql() -> dict[str, Any]:
        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "mysql_not_enabled"}
        try:
            from app.modules.data.services.mysql_access import mysql_connect

            conn = mysql_connect()
            try:
                conn.ping(reconnect=False)
                return {"status": "ok"}
            finally:
                conn.close()
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:50]}

    @staticmethod
    def probe_async_queue() -> dict[str, Any]:
        try:
            from app.infrastructure.task_queue import get_task_queue

            queue = get_task_queue()
            return {"status": "ok", "workers": queue._max_workers}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
