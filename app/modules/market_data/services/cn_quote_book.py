"""Delayed CN quote book: process memory + Redis. Pages read only; workers write.

Trading-session refresh is 5–15 minutes. Off-hours / weekends: if Redis is
empty, pull once so the page has the latest close. This is not TDX-tick realtime.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

BOOK_KEY = "quant:cn:quote:book"
BOOK_TTL_SEC = 24 * 3600

_memory_book: dict[str, Any] | None = None
_refreshing = False
_warm_attempted = False
_refresh_lock = threading.Lock()


def _cache():
    from app.infrastructure.cache.global_cache import get_global_cache

    return get_global_cache()


def load_cn_quote_book() -> list[dict[str, Any]]:
    global _memory_book
    payload = _memory_book
    if not isinstance(payload, dict) or not payload.get("items"):
        try:
            payload = _cache().get(BOOK_KEY)
        except Exception as exc:
            logger.debug("CN quote book redis get failed: %s", exc)
            payload = None
        if isinstance(payload, dict) and payload.get("items"):
            _memory_book = payload
    if not isinstance(payload, dict):
        return []
    items = payload.get("items") or []
    return [row for row in items if isinstance(row, dict)]


def save_cn_quote_book(items: list[dict[str, Any]], *, source: str = "refresh") -> None:
    global _memory_book
    if not items:
        return
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "count": len(items),
        "items": items,
    }
    _memory_book = payload
    try:
        _cache().set(BOOK_KEY, payload, ttl=BOOK_TTL_SEC)
    except Exception as exc:
        logger.debug("CN quote book redis set failed: %s", exc)
    logger.info("CN quote book saved: %s rows source=%s", len(items), source)


def clear_cn_quote_book() -> None:
    global _memory_book, _warm_attempted, _refreshing
    _memory_book = None
    _warm_attempted = False
    _refreshing = False
    try:
        _cache().delete(BOOK_KEY)
    except Exception:
        pass


def book_updated_at() -> str | None:
    payload = _memory_book
    if not isinstance(payload, dict):
        try:
            payload = _cache().get(BOOK_KEY)
        except Exception:
            payload = None
    if isinstance(payload, dict):
        value = payload.get("updated_at")
        return str(value) if value else None
    return None


def live_quote_pull_enabled() -> bool:
    """Page/boot may hit Tencent. CI sets ``CN_QUOTE_LIVE_PULL=0`` to keep E2E off the network."""
    from app.core.runtime_config import get_runtime_bool

    return get_runtime_bool("CN_QUOTE_LIVE_PULL", True)


def _is_cn_session(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 15)


def refresh_book_reason(*, force: bool = False, now: datetime | None = None) -> str | None:
    """Why the delayed book should be pulled.

    - ``empty``: Redis/memory book missing — pull once even off-hours / weekends
    - ``session``: trading session, periodic 5–15 min refresh
    - ``force``: caller override
    - ``None``: book exists and market is closed — keep the last pull
    """
    if force:
        return "force"
    if not load_cn_quote_book():
        return "empty"
    if _is_cn_session(now):
        return "session"
    return None


def should_refresh_book(*, force: bool = False, now: datetime | None = None) -> bool:
    return refresh_book_reason(force=force, now=now) is not None


def schedule_cn_quote_book_refresh(market_service: object | None) -> None:
    """One background refresh if the book is empty. Never blocks the request."""
    ensure_cn_quote_book(market_service)


def ensure_cn_quote_book(market_service: object | None) -> str:
    """If Redis is empty (nights/weekends included), pull once in the background.

    One attempt per process. Does not refresh an existing book off-hours.
    """
    global _refreshing, _warm_attempted
    if load_cn_quote_book():
        return "present"
    if not live_quote_pull_enabled():
        return "disabled"
    if market_service is None or not hasattr(market_service, "refresh_cn_quote_book"):
        return "no_service"
    with _refresh_lock:
        if _refreshing:
            return "in_flight"
        if _warm_attempted:
            return "attempted"
        _refreshing = True
        _warm_attempted = True

    def _run() -> None:
        global _refreshing
        try:
            market_service.refresh_cn_quote_book(allow_akshare=False)
        except Exception as exc:
            logger.warning("background CN quote book refresh failed: %s", exc)
        finally:
            with _refresh_lock:
                _refreshing = False

    threading.Thread(target=_run, name="cn-quote-book-warm", daemon=True).start()
    return "scheduled"
