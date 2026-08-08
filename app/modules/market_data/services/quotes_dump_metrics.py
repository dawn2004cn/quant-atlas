"""Counters for legacy full-market /quotes dumps (memory + optional Redis)."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATS: dict[str, Any] = {
    "full_dump_count": 0,
    "symbol_batch_count": 0,
    "last_full_dump_at": None,
    "last_full_dump_market": None,
    "last_full_dump_rows": 0,
}
_HISTORY: deque[dict[str, Any]] = deque(maxlen=24)

_REDIS_HASH = "quant:quotes:dump_stats"
_REDIS_LIST = "quant:quotes:dump_history"
_REDIS_TTL_SEC = 7 * 24 * 3600
_HISTORY_MAX = 24


def _redis_client() -> Any | None:
    try:
        from app.core.runtime_config import get_runtime
        from app.infrastructure.redis_client import RedisClientPool

        url = (get_runtime("REDIS_URL", "") or "").strip()
        if not url:
            return None
        return RedisClientPool.get(url).client
    except Exception as exc:
        logger.debug("quotes_dump_metrics redis unavailable: %s", exc)
        return None


def _append_history(event: dict[str, Any]) -> None:
    with _LOCK:
        _HISTORY.appendleft(dict(event))

    cli = _redis_client()
    if cli is None:
        return
    try:
        pipe = cli.pipeline()
        pipe.lpush(_REDIS_LIST, json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        pipe.ltrim(_REDIS_LIST, 0, _HISTORY_MAX - 1)
        pipe.expire(_REDIS_LIST, _REDIS_TTL_SEC)
        pipe.execute()
    except Exception as exc:
        logger.debug("quotes_dump_metrics history push failed: %s", exc)


def _read_history() -> list[dict[str, Any]]:
    cli = _redis_client()
    if cli is not None:
        try:
            raw_rows = cli.lrange(_REDIS_LIST, 0, _HISTORY_MAX - 1) or []
            out: list[dict[str, Any]] = []
            for raw in raw_rows:
                try:
                    item = json.loads(raw)
                except Exception:
                    continue
                if isinstance(item, dict):
                    out.append(item)
            if out:
                return out
        except Exception as exc:
            logger.debug("quotes_dump_metrics history read failed: %s", exc)

    with _LOCK:
        return [dict(x) for x in _HISTORY]


def record_full_dump(*, market: str, rows: int) -> None:
    """Record a full-market dump (no symbol filter) on GET /markets/<m>/quotes."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    market_s = str(market or "")
    rows_i = int(rows or 0)
    with _LOCK:
        _STATS["full_dump_count"] = int(_STATS["full_dump_count"]) + 1
        _STATS["last_full_dump_at"] = ts
        _STATS["last_full_dump_market"] = market_s
        _STATS["last_full_dump_rows"] = rows_i

    _append_history({"at": ts, "market": market_s, "rows": rows_i})

    cli = _redis_client()
    if cli is None:
        return
    try:
        pipe = cli.pipeline()
        pipe.hincrby(_REDIS_HASH, "full_dump_count", 1)
        pipe.hset(
            _REDIS_HASH,
            mapping={
                "last_full_dump_at": ts,
                "last_full_dump_market": market_s,
                "last_full_dump_rows": str(rows_i),
            },
        )
        pipe.expire(_REDIS_HASH, _REDIS_TTL_SEC)
        pipe.execute()
    except Exception as exc:
        logger.debug("quotes_dump_metrics redis record_full_dump failed: %s", exc)


def record_symbol_batch(*, market: str, symbols: int) -> None:
    """Record a preferred symbol-batch query on GET /markets/<m>/quotes."""
    _ = market
    size = int(symbols or 0)
    with _LOCK:
        _STATS["symbol_batch_count"] = int(_STATS["symbol_batch_count"]) + 1
        _STATS["last_symbol_batch_size"] = size

    cli = _redis_client()
    if cli is None:
        return
    try:
        pipe = cli.pipeline()
        pipe.hincrby(_REDIS_HASH, "symbol_batch_count", 1)
        pipe.hset(_REDIS_HASH, "last_symbol_batch_size", str(size))
        pipe.expire(_REDIS_HASH, _REDIS_TTL_SEC)
        pipe.execute()
    except Exception as exc:
        logger.debug("quotes_dump_metrics redis record_symbol_batch failed: %s", exc)


def get_quotes_dump_stats() -> dict[str, Any]:
    """Prefer Redis hash when available (cross-process); else in-process memory."""
    history = _read_history()
    # newest-first → oldest-first for sparkline
    trend_rows = [int(h.get("rows") or 0) for h in reversed(history)]

    cli = _redis_client()
    if cli is not None:
        try:
            raw = cli.hgetall(_REDIS_HASH) or {}
            if raw:
                return {
                    "full_dump_count": int(raw.get("full_dump_count") or 0),
                    "symbol_batch_count": int(raw.get("symbol_batch_count") or 0),
                    "last_full_dump_at": raw.get("last_full_dump_at") or None,
                    "last_full_dump_market": raw.get("last_full_dump_market") or None,
                    "last_full_dump_rows": int(raw.get("last_full_dump_rows") or 0),
                    "last_symbol_batch_size": int(raw.get("last_symbol_batch_size") or 0)
                    if raw.get("last_symbol_batch_size") is not None
                    else None,
                    "backend": "redis",
                    "recent_dumps": history,
                    "trend_rows": trend_rows,
                }
        except Exception as exc:
            logger.debug("quotes_dump_metrics redis read failed: %s", exc)

    with _LOCK:
        out = dict(_STATS)
    out["backend"] = "memory"
    out["recent_dumps"] = history
    out["trend_rows"] = trend_rows
    return out


def reset_quotes_dump_stats() -> None:
    """Test helper — clear memory and Redis keys."""
    with _LOCK:
        _STATS.clear()
        _STATS.update(
            {
                "full_dump_count": 0,
                "symbol_batch_count": 0,
                "last_full_dump_at": None,
                "last_full_dump_market": None,
                "last_full_dump_rows": 0,
            }
        )
        _HISTORY.clear()
    cli = _redis_client()
    if cli is None:
        return
    try:
        cli.delete(_REDIS_HASH, _REDIS_LIST)
    except Exception as exc:
        logger.debug("quotes_dump_metrics redis reset failed: %s", exc)
