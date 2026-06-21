from __future__ import annotations
"""东方财富 clist 拉取 A 股代码→行业（东财板块名），带进程内 TTL 缓存。"""


import math
import os
import random
import threading
import time
from typing import Any
import requests
from requests import exceptions as req_exc
from urllib3.exceptions import ProtocolError

from ...core.logger import get_logger
from . import DEFAULT_UA


logger = get_logger(__name__)

_lock = threading.Lock()
_cache: dict[str, str] = {}
_fetched_at: float = 0.0
# 拉取失败后在此时间之前不再访问东财（避免缓存过期 + 失败时每秒打满接口被拉黑）
_next_retry_at: float = 0.0
_consecutive_failures: int = 0

_TTL_SEC = int(os.getenv("EM_INDUSTRY_MAP_TTL_SEC", str(6 * 3600)))
_FAILURE_BACKOFF_BASE = int(os.getenv("EM_INDUSTRY_MAP_FAILURE_BACKOFF_SEC", "900"))
_FAILURE_BACKOFF_MAX = int(os.getenv("EM_INDUSTRY_MAP_FAILURE_BACKOFF_MAX_SEC", str(4 * 3600)))
_PAGE_DELAY_MIN = float(os.getenv("EM_INDUSTRY_MAP_PAGE_DELAY_MIN", "0.45"))
_PAGE_DELAY_MAX = float(os.getenv("EM_INDUSTRY_MAP_PAGE_DELAY_MAX", "1.15"))

_CLIST_URL = "https://82.push2.eastmoney.com/api/qt/clist/get"
_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_session_lock = threading.Lock()
_session: requests.Session | None = None


def _session_get() -> requests.Session:
    global _session
    with _session_lock:
        if _session is None:
            s = requests.Session()
            s.headers.update(_HEADERS)
            _session = s
        return _session


def _norm_code(f12: Any) -> str:
    s = "".join(ch for ch in str(f12 or "") if ch.isdigit())
    return s[-6:].zfill(6) if len(s) >= 6 else s.zfill(6) if s else ""


def _get_page_json(
    session: requests.Session,
    params: dict[str, Any],
    *,
    timeout: float,
    max_retries: int = 4,
) -> dict[str, Any]:
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            r = session.get(_CLIST_URL, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except (
            req_exc.ConnectionError,
            req_exc.ChunkedEncodingError,
            req_exc.Timeout,
            ProtocolError,
            OSError,
        ) as exc:
            last_exc = exc
            if attempt + 1 >= max_retries:
                break
            # 指数退避 + 抖动，降低被判定为爬虫的概率
            delay = (2**attempt) * random.uniform(0.7, 1.4)
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def fetch_cn_industry_map(*, timeout: float = 25.0, page_size: int = 500) -> dict[str, str]:
    """分页拉取沪深京 A 股 ``f12`` 代码与 ``f127`` 行业名；失败返回空 dict。"""
    out: dict[str, str] = {}
    params: dict[str, Any] = {
        "pn": "1",
        "pz": str(max(50, min(page_size, 500))),
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f12,f127",
    }
    session = _session_get()
    try:
        payload = _get_page_json(session, params, timeout=timeout)
        data = payload.get("data") or {}
        total = int(data.get("total") or 0)
        diff = data.get("diff") or []
        for row in diff:
            code = _norm_code(row.get("f12"))
            if not code:
                continue
            ind = str(row.get("f127") or "").strip()
            if ind:
                out[code] = ind
        pz = int(params["pz"])
        pages = max(1, int(math.ceil(total / float(pz)))) if total else 1
        for pn in range(2, pages + 1):
            time.sleep(random.uniform(_PAGE_DELAY_MIN, _PAGE_DELAY_MAX))
            params["pn"] = str(pn)
            payload2 = _get_page_json(session, params, timeout=timeout)
            for row in (payload2.get("data") or {}).get("diff") or []:
                code = _norm_code(row.get("f12"))
                if not code:
                    continue
                ind = str(row.get("f127") or "").strip()
                if ind:
                    out[code] = ind
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Eastmoney industry map fetch failed (will backoff, stale cache kept if any): %s",
            exc,
        )
        return {}
    return out


def get_cn_industry_map_cached(*, allow_fetch: bool = True) -> dict[str, str]:
    """进程内缓存；失败时在较长时间内不再重试，避免对东财高频打满。

    ``allow_fetch=False`` 时仅返回已有缓存（不自建网请求）。
    """
    global _cache, _fetched_at, _next_retry_at, _consecutive_failures
    now = time.time()
    with _lock:
        if _cache and (now - _fetched_at) < _TTL_SEC:
            return dict(_cache)
        if now < _next_retry_at:
            return dict(_cache)
        if not allow_fetch:
            return dict(_cache)

    fresh = fetch_cn_industry_map()

    with _lock:
        if fresh:
            _cache = fresh
            _fetched_at = time.time()
            _next_retry_at = 0.0
            _consecutive_failures = 0
        else:
            _consecutive_failures = min(_consecutive_failures + 1, 12)
            backoff = min(
                _FAILURE_BACKOFF_BASE * (2 ** (_consecutive_failures - 1)),
                _FAILURE_BACKOFF_MAX,
            )
            _next_retry_at = time.time() + backoff + random.uniform(5.0, 45.0)
            if not _cache:
                _fetched_at = time.time()
            logger.info(
                "Eastmoney industry map: next fetch no earlier than in %.0fs (failures=%s)",
                max(0.0, _next_retry_at - time.time()),
                _consecutive_failures,
            )
    return dict(_cache)
