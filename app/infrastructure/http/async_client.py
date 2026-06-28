from __future__ import annotations

"""Async HTTP client wrapper with connection pooling."""

from typing import Any

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)


class AsyncHttpClient:
    """Async HTTP client with built-in connection pooling and timeout.

    Previously this class fell back to synchronous ``requests`` when ``httpx``
    was unavailable. That fallback blocked the async event loop, so it has been
    removed; ``httpx`` is now a core dependency.
    """

    _instance: AsyncHttpClient | None = None
    _client: httpx.AsyncClient | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of httpx async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Perform async GET request."""
        client = await self._get_client()
        try:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return {"ok": True, "data": response.json(), "status": response.status_code}
        except Exception as e:
            logger.error("Async GET failed for %s: %s", url, e)
            return {"ok": False, "error": str(e)}

    async def post(self, url: str, **kwargs) -> dict[str, Any]:
        """Perform async POST request."""
        client = await self._get_client()
        try:
            response = await client.post(url, **kwargs)
            response.raise_for_status()
            return {"ok": True, "data": response.json(), "status": response.status_code}
        except Exception as e:
            logger.error("Async POST failed for %s: %s", url, e)
            return {"ok": False, "error": str(e)}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


async_http = AsyncHttpClient()
