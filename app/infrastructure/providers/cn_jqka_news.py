from __future__ import annotations
"""同花顺实时新闻 Provider - https://news.10jqka.com.cn/realtimenews.html"""


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

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_DEFAULT_TTL = 60.0


def _cached(key: str, ttl: float, fetch_fn) -> list[dict[str, Any]]:
    with _CACHE_LOCK:
        now = time.time()
        if key in _CACHE:
            ts, data = _CACHE[key]
            if now - ts < ttl:
                return data
    data = fetch_fn()
    with _CACHE_LOCK:
        _CACHE[key] = (now, data)
    return data


def fetch_10jqka_realtime_news(
    *,
    limit: int = 40,
    timeout: float = 15.0,
    category: str = "all",
) -> list[dict[str, Any]]:
    """获取同花顺实时新闻 - 使用现有接口

    Args:
        limit: 返回条数限制
        timeout: 超时时间
        category: 新闻分类 (all/cj/gg/zx/cy) - 暂不支持细分

    Returns:
        list[dict] - 新闻列表
    """
    def _load() -> list[dict[str, Any]]:
        # 使用 cn_portal_news 中已有的同花顺接口
        from app.infrastructure.providers.cn_portal_news import fetch_10jqka_gdxw_headlines
        try:
            news = fetch_10jqka_gdxw_headlines(limit=limit, timeout=timeout)
            # 标记来源
            for n in news:
                n["source"] = "10jqka_realtime"
            return news
        except Exception as e:
            logger.warning(f"同花顺实时新闻获取失败: {e}")
            return []

    return _cached(f"10jqka_realtime_{category}", _DEFAULT_TTL, _load)[:limit]


def fetch_10jqka_stock_news(
    symbol: str,
    *,
    limit: int = 20,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """获取特定股票的同花顺新闻

    Args:
        symbol: 股票代码 (如 000001, 600000)
        limit: 返回条数限制
        timeout: 超时时间

    Returns:
        list[dict] - 新闻列表
    """
    code6 = symbol[-6:] if len(symbol) >= 6 else symbol

    def _load() -> list[dict[str, Any]]:
        url = f"https://stockpage.10jqka.com.cn/{code6}/news/"

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            resp.encoding = "utf-8"
        except Exception as e:
            logger.warning(f"同花顺股票新闻请求失败: {e}")
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        out: list[dict[str, Any]] = []

        for a_tag in soup.select("a[href]"):
            try:
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")

                if not title or len(title) < 5:
                    continue

                if not href or "javascript" in href:
                    continue

                # 过滤有效新闻链接
                if "article" not in href and "news" not in href:
                    continue

                if not href.startswith("http"):
                    href = f"https://stockpage.10jqka.com.cn{href}"

                out.append({
                    "title": title,
                    "url": href,
                    "published_at": "",
                    "source": "10jqka_stock",
                    "summary": "",
                })

                if len(out) >= limit:
                    break
            except Exception:
                continue

        return out

    return _cached(f"10jqka_stock_{code6}", _DEFAULT_TTL, _load)[:limit]


class JqkaNewsProvider:
    """同花顺新闻 Provider"""

    def __init__(self, ttl_seconds: float = 60.0):
        self._ttl = ttl_seconds

    def get_realtime_news(
        self,
        *,
        limit: int = 40,
        category: str = "all",
    ) -> list[dict[str, Any]]:
        """获取实时新闻

        Args:
            limit: 返回条数
            category: 分类 (all/cj/gg/zx/cy)

        Returns:
            list[dict] - 新闻列表
        """
        return fetch_10jqka_realtime_news(limit=limit, category=category)

    def get_stock_news(
        self,
        symbol: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """获取特定股票新闻

        Args:
            symbol: 股票代码
            limit: 返回条数

        Returns:
            list[dict] - 新闻列表
        """
        return fetch_10jqka_stock_news(symbol=symbol, limit=limit)

    def get_all_news(
        self,
        *,
        realtime_limit: int = 20,
        stock_symbol: str | None = None,
        stock_limit: int = 10,
    ) -> list[dict[str, Any]]:
        """获取所有新闻（实时 + 可选个股）

        Args:
            realtime_limit: 实时新闻条数
            stock_symbol: 可选，指定股票代码
            stock_limit: 个股新闻条数

        Returns:
            list[dict] - 合并后的新闻列表
        """
        news = self.get_realtime_news(limit=realtime_limit)

        if stock_symbol:
            stock_news = self.get_stock_news(stock_symbol, limit=stock_limit)
            news.extend(stock_news)

        return news


def create_jqka_news_provider() -> JqkaNewsProvider:
    """创建同花顺新闻 Provider 实例"""
    return JqkaNewsProvider()
