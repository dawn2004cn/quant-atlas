"""Bootstrap: TDX → Redis quote feed background thread."""

from __future__ import annotations

import threading
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool
from app.infrastructure.realtime.tdx_redis_quote_store import tdx_redis_feed_enabled

logger = get_logger(__name__)

_feed_thread: threading.Thread | None = None


def init_tdx_redis_feed(app: Any, settings: Any) -> dict[str, Any]:
    """Start TDX→Redis poller during CN trading session (9:15-11:30 / 13:00-15:00)."""
    global _feed_thread
    meta: dict[str, Any] = {"tdx_redis_feed": False}
    if not tdx_redis_feed_enabled():
        logger.info("TDX_REDIS_FEED disabled")
        return meta
    if not get_runtime_bool("TDX_REDIS_FEED_ON_BOOT", True):
        return meta

    from app.infrastructure.realtime.tdx_redis_quote_store import TdxRedisQuoteStore
    from app.modules.market_data.services.tdx_realtime_feed_service import (
        feed_interval_sec,
        run_feed_loop,
    )

    store = TdxRedisQuoteStore()
    if not store.available:
        logger.warning("TDX Redis feed skipped: Redis unavailable (set REDIS_URL)")
        return meta

    if _feed_thread is None or not _feed_thread.is_alive():
        _feed_thread = threading.Thread(
            target=run_feed_loop,
            name="tdx-redis-quote-feed",
            daemon=True,
        )
        _feed_thread.start()
        meta["tdx_redis_feed"] = True
        logger.info(
            "TDX→Redis quote feed started (interval=%ss, session 9:15-11:30 / 13:00-15:00)",
            feed_interval_sec(),
        )
    return meta


__all__ = ["init_tdx_redis_feed"]
