from __future__ import annotations
"""Async market data provider using aiotdx or httpx."""


from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


class AsyncMarketProvider:
    """Async market data provider with TDX fallback."""

    def __init__(self):
        self._tdx = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize async providers."""
        if self._initialized:
            return
        try:
            from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
            self._tdx = create_tdx_provider()
            self._initialized = True
            logger.info("AsyncMarketProvider initialized with TDX")
        except Exception as e:
            logger.warning("TDX provider init failed: %s", e)
            self._initialized = True

    async def get_quote(self, code: str, market: str = "CN") -> dict[str, Any]:
        """Get real-time quote asynchronously."""
        if not self._initialized:
            await self.initialize()

        if self._tdx:
            try:
                return await self._async_quote_from_tdx(code, market)
            except Exception as e:
                logger.debug("TDX quote failed: %s", e)

        return await self._fallback_quote(code, market)

    async def get_history(
        self,
        code: str,
        market: str,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Get history data asynchronously."""
        if not self._initialized:
            await self.initialize()

        if self._tdx:
            try:
                return self._tdx.get_history(code, market, start, end)
            except Exception as e:
                logger.debug("TDX history failed: %s", e)

        return await self._fallback_history(code, market, start, end)

    async def _async_quote_from_tdx(self, code: str, market: str) -> dict[str, Any]:
        """Get quote from TDX provider."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._tdx.get_quote(code, market))

    async def _fallback_quote(self, code: str, market: str) -> dict[str, Any]:
        """Fallback to AkShare for quotes."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._get_akshare_quote(code))
        except Exception as e:
            logger.error("AkShare quote failed: %s", e)
            return {"code": code, "price": 0, "error": str(e)}

    async def _fallback_history(
        self,
        code: str,
        market: str,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Fallback to AkShare for history."""
        try:
            import akshare as ak
            import asyncio
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_zh_a_hist(symbol=code, start_date=start.replace("-", ""), end_date=end.replace("-", ""), adjust="qfq")
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
        except Exception as e:
            logger.error("AkShare history failed: %s", e)
        return []

    def _get_akshare_quote(self, code: str) -> dict[str, Any]:
        """Sync wrapper for AkShare quote."""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "code": str(r.get("代码", code)),
                    "name": str(r.get("名称", "")),
                    "price": float(r.get("最新价", 0) or 0),
                    "change_pct": float(r.get("涨跌幅", 0) or 0),
                }
        except Exception as e:
            logger.warning("async_market_provider.py._get_akshare_quote: %s", e)
        return {"code": code, "price": 0}


_async_market_provider: AsyncMarketProvider | None = None


def get_async_market_provider() -> AsyncMarketProvider:
    """Get singleton async market provider."""
    global _async_market_provider
    if _async_market_provider is None:
        _async_market_provider = AsyncMarketProvider()
    return _async_market_provider


def to_async_provider(sync_provider: Any) -> AsyncMarketProvider:
    """Wrap sync provider to async interface."""
    class WrappedProvider(AsyncMarketProvider):
        def __init__(self, provider):
            super().__init__()
            self._sync_provider = provider
            self._initialized = True

        async def get_quote(self, code: str, market: str = "CN") -> dict[str, Any]:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: getattr(self._sync_provider, "get_quote", lambda c, m: {})(code, market)
            )

        async def get_history(self, code: str, market: str, start: str, end: str) -> list[dict[str, Any]]:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: getattr(self._sync_provider, "get_history", lambda *a: [])(code, market, start, end)
            )

    return WrappedProvider(sync_provider)


AsyncMarketDataProvider = AsyncMarketProvider
