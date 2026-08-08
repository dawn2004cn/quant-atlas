from __future__ import annotations

"""Celery task: inspect quotes full-dump pressure and optionally auto-dispatch alerts."""

from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int

logger = get_logger(__name__)


def run_quotes_dump_monitor(
    *,
    auto_dispatch: bool | None = None,
) -> dict[str, Any]:
    """Check dump counters against threshold; optionally trigger alert dispatch."""
    from app.modules.market_data.services.quotes_dump_metrics import get_quotes_dump_stats

    stats = get_quotes_dump_stats() or {}
    dump_n = int(stats.get("full_dump_count") or 0)
    threshold = max(1, int(get_runtime_int("QUOTES_FULL_DUMP_WARN_THRESHOLD", 1)))
    warn = dump_n >= threshold
    do_dispatch = (
        auto_dispatch
        if auto_dispatch is not None
        else get_runtime_bool("QUOTES_DUMP_AUTO_DISPATCH", False)
    )

    out: dict[str, Any] = {
        "ok": True,
        "warn": warn,
        "full_dump_count": dump_n,
        "threshold": threshold,
        "backend": stats.get("backend"),
        "last_full_dump_at": stats.get("last_full_dump_at"),
        "last_full_dump_market": stats.get("last_full_dump_market"),
        "last_full_dump_rows": stats.get("last_full_dump_rows"),
        "preferred_endpoint": "quotes/page",
        "auto_dispatch": do_dispatch,
        "dispatched": False,
    }

    if not warn:
        out["skipped"] = True
        out["reason"] = "below_threshold"
        return out

    if not do_dispatch:
        out["reason"] = "warn_without_auto_dispatch"
        return out

    try:
        from app.tasks.alert_dispatch_tasks import run_dispatch_alert_notifications

        dispatch_payload = run_dispatch_alert_notifications(respect_dedup=True)
        out["dispatched"] = True
        out["dispatch"] = dispatch_payload
        out["reason"] = "auto_dispatched"
    except Exception as exc:
        logger.exception("quotes_dump_monitor auto_dispatch failed")
        out["ok"] = False
        out["error"] = str(exc)
        out["reason"] = "auto_dispatch_failed"
    return out


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.quotes_dump_monitor_tasks.quotes_dump_monitor_tick")
    def quotes_dump_monitor_tick(auto_dispatch: bool | None = None) -> dict[str, Any]:
        try:
            return run_quotes_dump_monitor(auto_dispatch=auto_dispatch)
        except Exception as exc:
            logger.exception("quotes_dump_monitor_tick failed")
            return {"ok": False, "error": str(exc)}

else:
    quotes_dump_monitor_tick = None  # type: ignore[misc, assignment]
