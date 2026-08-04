from __future__ import annotations

"""Celery task: dispatch alert center feed to external channels."""

from typing import Any

from app.core.logger import get_logger
from app.modules.system.services.system.alert_notification_service import AlertNotificationService

logger = get_logger(__name__)


def run_dispatch_alert_notifications(
    *,
    min_level: str | None = None,
    limit: int | None = None,
    channels: list[str] | None = None,
    respect_dedup: bool = True,
) -> dict[str, Any]:
    from app.core.runtime_config import get_runtime, get_runtime_int

    resolved_level = (min_level or get_runtime("ALERT_DISPATCH_MIN_LEVEL", "warning") or "warning").strip().lower()
    resolved_limit = limit if limit is not None else get_runtime_int("ALERT_DISPATCH_LIMIT", 20)
    svc = AlertNotificationService()
    result = svc.dispatch(
        min_level=resolved_level,  # type: ignore[arg-type]
        limit=max(1, min(resolved_limit, 50)),
        channel_names=channels,
        respect_dedup=respect_dedup,
    )
    payload = result.model_dump(mode="json")
    payload["ok"] = bool(result.sent) or result.deduplicated or result.skipped
    try:
        from app.modules.market_data.services.quotes_dump_metrics import get_quotes_dump_stats

        stats = get_quotes_dump_stats() or {}
        dump_n = int(stats.get("full_dump_count") or 0)
        threshold = max(1, int(get_runtime_int("QUOTES_FULL_DUMP_WARN_THRESHOLD", 1)))
        payload["quotes_dump"] = {
            "full_dump_count": dump_n,
            "threshold": threshold,
            "warn": dump_n >= threshold,
            "preferred_endpoint": "quotes/page",
        }
    except Exception as exc:
        logger.debug("dispatch quotes_dump annotate failed: %s", exc)
        payload["quotes_dump"] = {"warn": False, "error": str(exc)}
    return payload


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.alert_dispatch_tasks.dispatch_alert_notifications")
    def dispatch_alert_notifications(
        min_level: str | None = None,
        limit: int | None = None,
        channels: list[str] | None = None,
        respect_dedup: bool = True,
    ) -> dict[str, Any]:
        try:
            return run_dispatch_alert_notifications(
                min_level=min_level,
                limit=limit,
                channels=channels,
                respect_dedup=respect_dedup,
            )
        except Exception as exc:
            logger.exception("dispatch_alert_notifications failed")
            return {"ok": False, "error": str(exc)}

else:
    dispatch_alert_notifications = None  # type: ignore[misc, assignment]
