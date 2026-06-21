from __future__ import annotations
"""雪球用户动态 Provider - https://xueqiu.com/u/{user_id}"""


import re
import threading
import time
from typing import Any

import requests

from ...core.logger import get_logger
from . import DEFAULT_UA

logger = get_logger(__name__)

_HEADERS = {"User-Agent": DEFAULT_UA}

_DEFAULT_COOKIE = "device_id=886190492bbc53bc8942db37918c35f5; s=ag12ey0glh; xq_a_token=20458f74230aee45906ecb90d8c70ff43daa3837; xqat=20458f74230aee45906ecb90d8c70ff43daa3837; xq_r_token=fa5fac8aea31fef0733c31a1c3670554e9365bda; u=111773738372742"

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_DEFAULT_TTL = 120.0


def _cached(key: str, ttl: float, fetch_fn) -> list[dict[str, Any]]:
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return list(hit[1])
    try:
        data = fetch_fn()
    except Exception as exc:
        logger.warning("cn_xueqiu_news %s failed: %s", key, exc)
        data = []
    with _CACHE_LOCK:
        _CACHE[key] = (now, data)
    return list(data)


def fetch_xueqiu_user_timeline(
    user_id: str,
    *,
    limit: int = 20,
    timeout: float = 15.0,
    cookie: str | None = None,
) -> list[dict[str, Any]]:
    """获取雪球用户动态

    Args:
        user_id: 雪球用户ID (如 5124430882)
        limit: 返回条数限制
        timeout: 超时时间
        cookie: 可选，用于认证的cookie

    Returns:
        list[dict] - 用户动态列表
    """

    def _load() -> list[dict[str, Any]]:
        url = f"https://xueqiu.com/statuses/user_timeline.json"
        params = {
            "user_id": user_id,
            "count": limit,
            "type": "feed",
        }

        cookies = {}
        if cookie:
            for item in cookie.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies[k] = v

        try:
            resp = requests.get(
                url,
                headers=_HEADERS,
                params=params,
                cookies=cookies,
                timeout=timeout,
            )
            resp.encoding = "utf-8"
        except Exception as e:
            logger.warning(f"雪球用户动态请求失败: {e}")
            return []

        try:
            data = resp.json()
        except Exception:
            logger.warning("雪球返回数据解析失败")
            return []

        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        statuses = data.get("statuses", [])
        for item in statuses:
            try:
                text = item.get("text", "")
                if not text:
                    continue

                from bs4 import BeautifulSoup

                soup = BeautifulSoup(text, "html.parser")
                title = soup.get_text(strip=True)

                if len(title) < 5:
                    continue

                article_id = item.get("id", "")
                if article_id in seen:
                    continue
                seen.add(article_id)

                created_at = item.get("created_at", "")
                if created_at:
                    try:
                        ts = int(created_at) / 1000
                        import datetime

                        created_at = datetime.datetime.fromtimestamp(ts).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except Exception as e:
                        logger.warning("cn_xueqiu_news.py.fetch_xueqiu_user_timeline: %s", e)

                user = item.get("user", {})
                source_name = user.get("screen_name", "") or f"xueqiu_{user_id}"

                out.append({
                    "title": title[:200] if len(title) > 200 else title,
                    "url": f"https://xueqiu.com/status/{article_id}",
                    "published_at": created_at,
                    "source": source_name,
                    "summary": text[:300] if len(text) > 300 else text,
                })

                if len(out) >= limit:
                    break
            except Exception:
                continue

        return out

    return _cached(f"xueqiu_{user_id}", _DEFAULT_TTL, _load)[:limit]


def fetch_xueqiu_user_posts(
    user_id: str,
    *,
    limit: int = 20,
    timeout: float = 15.0,
    cookie: str | None = None,
) -> list[dict[str, Any]]:
    """获取雪球用户原创文章（不含转发）

    Args:
        user_id: 雪球用户ID
        limit: 返回条数限制
        timeout: 超时时间
        cookie: 可选，用于认证的cookie

    Returns:
        list[dict] - 用户文章列表
    """

    def _load() -> list[dict[str, Any]]:
        url = f"https://xueqiu.com/statuses/user_timeline.json"
        params = {
            "user_id": user_id,
            "count": limit,
            "type": "status",
        }

        cookies = {}
        if cookie:
            for item in cookie.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies[k] = v

        try:
            resp = requests.get(
                url,
                headers=_HEADERS,
                params=params,
                cookies=cookies,
                timeout=timeout,
            )
            resp.encoding = "utf-8"
        except Exception as e:
            logger.warning(f"雪球用户文章请求失败: {e}")
            return []

        try:
            data = resp.json()
        except Exception:
            logger.warning("雪球返回数据解析失败")
            return []

        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        statuses = data.get("statuses", [])
        for item in statuses:
            try:
                text = item.get("text", "")
                if not text:
                    continue

                from bs4 import BeautifulSoup

                soup = BeautifulSoup(text, "html.parser")
                title = soup.get_text(strip=True)

                if len(title) < 5:
                    continue

                article_id = item.get("id", "")
                if article_id in seen:
                    continue
                seen.add(article_id)

                created_at = item.get("created_at", "")
                if created_at:
                    try:
                        ts = int(created_at) / 1000
                        import datetime

                        created_at = datetime.datetime.fromtimestamp(ts).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except Exception as e:
                        logger.warning("cn_xueqiu_news.py.fetch_xueqiu_user_posts: %s", e)

                out.append({
                    "title": title[:200] if len(title) > 200 else title,
                    "url": f"https://xueqiu.com/status/{article_id}",
                    "published_at": created_at,
                    "source": f"xueqiu_{user_id}",
                    "summary": text[:300] if len(text) > 300 else text,
                })

                if len(out) >= limit:
                    break
            except Exception:
                continue

        return out

    return _cached(f"xueqiu_posts_{user_id}", _DEFAULT_TTL, _load)[:limit]


class XueqiuNewsProvider:
    """雪球新闻 Provider"""

    def __init__(
        self,
        user_id: str = "5124430882",
        cookie: str | None = None,
        ttl_seconds: float = 120.0,
    ):
        self._user_id = user_id
        self._cookie = cookie or _DEFAULT_COOKIE
        self._ttl = ttl_seconds

    def set_user_id(self, user_id: str) -> None:
        """设置雪球用户ID"""
        self._user_id = user_id

    def get_user_timeline(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """获取用户动态（包含转发）

        Args:
            limit: 返回条数

        Returns:
            list[dict] - 用户动态列表
        """
        return fetch_xueqiu_user_timeline(self._user_id, limit=limit, cookie=self._cookie)

    def get_user_posts(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """获取用户原创文章

        Args:
            limit: 返回条数

        Returns:
            list[dict] - 用户文章列表
        """
        return fetch_xueqiu_user_posts(self._user_id, limit=limit, cookie=self._cookie)

    def get_all(
        self,
        limit: int = 30,
        *,
        timeline_limit: int = 15,
        posts_limit: int = 15,
    ) -> list[dict[str, Any]]:
        """获取用户所有动态

        Args:
            limit: 总返回条数
            timeline_limit: 动态条数
            posts_limit: 文章条数

        Returns:
            list[dict] - 合并后的列表
        """
        timeline = self.get_user_timeline(limit=timeline_limit)
        posts = self.get_user_posts(limit=posts_limit)

        combined = posts + timeline

        combined.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True,
        )

        return combined[:limit]


def create_xueqiu_news_provider(
    user_id: str = "5124430882",
    cookie: str | None = None,
) -> XueqiuNewsProvider:
    """创建雪球新闻 Provider 实例"""
    return XueqiuNewsProvider(user_id=user_id, cookie=cookie)