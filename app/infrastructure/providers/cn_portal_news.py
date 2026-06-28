from __future__ import annotations

"""东方财富滚动、同花顺股道等门户快讯（requests + BeautifulSoup），供 NewsProvider 合并。"""


import re
import threading
import time
from typing import Any

import requests

from ...core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _DEFAULT_UA}

# 简单 TTL 内存缓存，降低对门户站请求频率
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_DEFAULT_TTL = 120.0

_TIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})")
_JQKA_TIME_RE = re.compile(r"\d{2}月\d{2}日")


def _cached(key: str, ttl: float, fetch_fn) -> list[dict[str, Any]]:
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return list(hit[1])
    try:
        data = fetch_fn()
    except Exception as exc:
        logger.warning("cn_portal_news %s failed: %s", key, exc)
        data = []
    with _CACHE_LOCK:
        _CACHE[key] = (now, data)
    return list(data)


def _normalize_url(url: str, base: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    if u.startswith("/"):
        return base.rstrip("/") + u
    return u


def fetch_eastmoney_roll_headlines(*, limit: int = 40, timeout: float = 12.0) -> list[dict[str, Any]]:
    """东方财富滚动频道 https://roll.eastmoney.com/"""

    def _load() -> list[dict[str, Any]]:
        from bs4 import BeautifulSoup

        resp = requests.get(
            "https://roll.eastmoney.com/",
            headers=_HEADERS,
            timeout=timeout,
        )
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            if "finance.eastmoney.com/a/" not in href:
                continue
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 4:
                continue
            url = _normalize_url(href, "https://roll.eastmoney.com")
            key = url or title
            if key in seen:
                continue
            seen.add(key)
            pub = ""
            parent = a.parent
            for _ in range(6):
                if parent is None:
                    break
                text = parent.get_text(" ", strip=True)
                m = _TIME_RE.search(text)
                if m:
                    pub = m.group(1)
                    break
                parent = parent.parent
            out.append(
                {
                    "title": title,
                    "url": url,
                    "published_at": pub,
                    "source": "eastmoney_roll",
                    "summary": "",
                }
            )
            if len(out) >= limit:
                break
        return out

    return _cached("eastmoney_roll", _DEFAULT_TTL, _load)[:limit]


def fetch_10jqka_gdxw_headlines(*, limit: int = 40, timeout: float = 12.0) -> list[dict[str, Any]]:
    """同花顺股道新闻列表 https://news.10jqka.com.cn/gdxw_list/index.shtml"""

    def _load() -> list[dict[str, Any]]:
        from bs4 import BeautifulSoup

        resp = requests.get(
            "https://news.10jqka.com.cn/gdxw_list/index.shtml",
            headers=_HEADERS,
            timeout=timeout,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.select('a[href*="10jqka.com.cn"]'):
            href = (a.get("href") or "").strip()
            if not href or "javascript:" in href:
                continue
            if "news.10jqka.com.cn" not in href:
                continue
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 4:
                continue
            url = _normalize_url(href, "https://news.10jqka.com.cn")
            key = url or title
            if key in seen:
                continue
            seen.add(key)
            pub = ""
            li = a.find_parent("li")
            if li:
                for node in li.stripped_strings:
                    if _JQKA_TIME_RE.search(node):
                        pub = node.strip()
                        break
            out.append(
                {
                    "title": title,
                    "url": url,
                    "published_at": pub,
                    "source": "10jqka_gdxw",
                    "summary": "",
                }
            )
            if len(out) >= limit:
                break
        return out

    return _cached("10jqka_gdxw", _DEFAULT_TTL, _load)[:limit]


def portal_headlines_cn(*, limit_per_source: int = 30) -> list[dict[str, Any]]:
    """合并两路门户快讯（各截断），用于全市场摘要。"""
    em = fetch_eastmoney_roll_headlines(limit=limit_per_source)
    th = fetch_10jqka_gdxw_headlines(limit=limit_per_source)
    return em + th


def filter_headlines_for_symbol(headlines: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    """标题中出现规范化 6 位代码则视为与标的相关（避免误匹配过短数字）。"""
    from ...infrastructure.mappers.symbol_normalizer import SymbolNormalizer

    code = SymbolNormalizer.normalize_code(symbol)
    if not code or code == "000000":
        return []
    matched: list[dict[str, Any]] = []
    for h in headlines:
        t = str(h.get("title") or "")
        if code in t:
            matched.append(h)
    return matched
