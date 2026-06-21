from __future__ import annotations

"""进程内 xdxr 缓存 + 并发限流，降低全量同步时对 TDX 服务器的重复 TCP 请求。"""

import threading
from collections import OrderedDict
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_int

logger = get_logger(__name__)

_CACHE_LOCK = threading.Lock()
_FETCH_SEM: threading.Semaphore | None = None
_CACHE: OrderedDict[str, pd.DataFrame] = OrderedDict()


def _cache_max_size() -> int:
    return max(500, min(get_runtime_int("TDX_XDXR_CACHE_SIZE", 12000), 50000))


def _fetch_max_concurrent() -> int:
    return max(1, min(get_runtime_int("TDX_XDXR_MAX_CONCURRENT", 4), 32))


def _get_fetch_sem() -> threading.Semaphore:
    global _FETCH_SEM
    if _FETCH_SEM is None:
        _FETCH_SEM = threading.Semaphore(_fetch_max_concurrent())
    return _FETCH_SEM


def _cache_key(market: str, code: str) -> str:
    return f"{market.lower()}:{code}"


def get_cached_xdxr(market: str, code: str, fetcher: Any) -> pd.DataFrame:
    """``fetcher(market, code) -> DataFrame``；命中缓存则不再访问 TDX。"""
    key = _cache_key(market, code)
    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]

    with _get_fetch_sem():
        with _CACHE_LOCK:
            if key in _CACHE:
                _CACHE.move_to_end(key)
                return _CACHE[key]
        try:
            df = fetcher(market, code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("xdxr fetch %s: %s", key, exc)
            df = pd.DataFrame()
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame()

    with _CACHE_LOCK:
        _CACHE[key] = df
        _CACHE.move_to_end(key)
        while len(_CACHE) > _cache_max_size():
            _CACHE.popitem(last=False)
    return df


def clear_xdxr_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
