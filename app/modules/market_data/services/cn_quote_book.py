"""Delayed CN quote book: process memory + Redis. Pages read only; workers write.

Trading-session refresh is 5–15 minutes. This is not TDX-tick realtime.
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
    global _memory_book
    _memory_book = None
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


def _is_cn_session(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 15)


def schedule_cn_quote_book_refresh(market_service: object | None) -> None:
    """One background refresh if the book is empty. Never blocks the request."""
    global _refreshing
    if market_service is None or not hasattr(market_service, "refresh_cn_quote_book"):
        return
    if load_cn_quote_book():
        return
    with _refresh_lock:
        if _refreshing:
            return
        _refreshing = True

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


def should_refresh_book(*, force: bool = False) -> bool:
    if force:
        return True
    if not load_cn_quote_book():
        return True
    return _is_cn_session()
