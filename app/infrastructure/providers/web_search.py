from __future__ import annotations
"""Web search provider implementations (Tavily, Bocha) ported from daily_stock_analysis."""


from typing import Any

import requests

from ...core.runtime_config import get_runtime
from ...domain.ports import WebSearchProvider
from app.core.logger import get_logger

logger = get_logger(__name__)


class MultiEngineSearchProvider(WebSearchProvider):
    """协调多个搜索引擎的复合提供者。"""

    def __init__(self):
        self._providers = []
        
        # Tavily
        tavily_key = get_runtime("TAVILY_API_KEY")
        if tavily_key:
            self._providers.append(TavilySearchProvider(tavily_key))
            
        # Bocha
        bocha_key = get_runtime("BOCHA_API_KEY")
        if bocha_key:
            self._providers.append(BochaSearchProvider(bocha_key))

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """依次尝试可用的搜索引擎。"""
        if not self._providers:
            logger.warning("未配置任何 Web 搜索 API Key (TAVILY_API_KEY 或 BOCHA_API_KEY)")
            return []

        for provider in self._providers:
            try:
                results = provider.search(query, max_results)
                if results:
                    return results
            except Exception as e:
                logger.error(f"搜索引擎 {provider.__class__.__name__} 失败: {e}")
                continue
        
        return []


class TavilySearchProvider(WebSearchProvider):
    """Tavily 搜索引擎适配器。"""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self._api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                    "snippet": item.get("content")[:200],
                    "source": "Tavily"
                })
            return results
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return []


class BochaSearchProvider(WebSearchProvider):
    """博查搜索引擎适配器。"""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        try:
            url = "https://api.bocha.cn/v1/web-search"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "freshness": "oneWeek",
                "count": max_results
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 博查返回结构通常在 data.webPages.value
            results = []
            pages = data.get("data", {}).get("webPages", {}).get("value", [])
            for item in pages:
                results.append({
                    "title": item.get("name"),
                    "url": item.get("url"),
                    "content": item.get("snippet"),
                    "snippet": item.get("snippet"),
                    "source": "Bocha"
                })
            return results
        except Exception as e:
            logger.error(f"Bocha 搜索失败: {e}")
            return []
