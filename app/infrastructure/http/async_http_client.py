from __future__ import annotations
"""Async HTTP Client using httpx.

Phase 46: 全异步 HTTP 客户端，替换所有 requests.get 调用。

Benefits:
- Fully async/await compatible
- Connection pooling
- HTTP/2 support
- Better performance than requests + run_in_executor
"""


import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """Async HTTP client with connection pooling.

    Usage:
        client = AsyncHTTPClient()
        async with client:
            response = await client.get("https://api.example.com/data")
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ):
        self._base_url = base_url
        self._timeout = httpx.Timeout(timeout)
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                limits=self._limits,
                http2=True,
            )
        return self._client

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make async GET request."""
        client = await self._get_client()
        try:
            response = await client.get(url, params=params, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e} - {url}")
            raise

    async def post(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make async POST request."""
        client = await self._get_client()
        try:
            response = await client.post(url, data=data, json=json, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e} - {url}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncHTTPClient":
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# Global client instance
_global_client: AsyncHTTPClient | None = None


def get_async_http_client() -> AsyncHTTPClient:
    """Get the global async HTTP client."""
    global _global_client
    if _global_client is None:
        _global_client = AsyncHTTPClient()
    return _global_client


async def async_get(url: str, **kwargs: Any) -> httpx.Response:
    """Convenience function for async GET requests."""
    client = get_async_http_client()
    return await client.get(url, **kwargs)


async def async_post(url: str, **kwargs: Any) -> httpx.Response:
    """Convenience function for async POST requests."""
    client = get_async_http_client()
    return await client.post(url, **kwargs)


__all__ = [
    "AsyncHTTPClient",
    "get_async_http_client",
    "async_get",
    "async_post",
]