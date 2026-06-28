from __future__ import annotations

"""Per-market Redis Stream execution driver with paper fallback."""

import logging

from app.domain.execution.driver_protocol import (
    OrderStatus,
    TradeRequest,
    TradeResponse,
)
from app.infrastructure.execution.driver.redis_executor import RedisStreamExecutor
from app.infrastructure.execution.drivers.paper_driver import PaperExecutionDriver

logger = logging.getLogger(__name__)


class RedisMarketExecutionDriver:
    """Market-scoped Redis queue driver; falls back to paper when Redis/worker unavailable."""

    def __init__(
        self,
        *,
        market: str,
        exchange: str,
        redis_url: str = "",
        queue_name: str = "",
        fallback_paper: bool = True,
        timeout: float = 2.0,
    ) -> None:
        self._market = market.upper()
        self._exchange = exchange
        self._redis_url = (redis_url or "").strip()
        self._queue_name = (queue_name or f"borderless_exec_{market.lower()}").strip()
        self._timeout = max(0.5, float(timeout))
        self._fallback_enabled = fallback_paper
        self._paper = PaperExecutionDriver(market=market, exchange=exchange)
        self._executor: RedisStreamExecutor | None = None

    def describe(self) -> dict[str, str | bool]:
        return {
            "market": self._market,
            "exchange": self._exchange,
            "backend": "redis" if self._redis_available() else "redis_paper_fallback",
            "queue": self._queue_name,
            "fallback_paper": self._fallback_enabled,
        }

    def _get_executor(self) -> RedisStreamExecutor | None:
        if not self._redis_url:
            return None
        if self._executor is None:
            self._executor = RedisStreamExecutor(
                redis_url=self._redis_url,
                queue_name=self._queue_name,
                timeout=self._timeout,
            )
        return self._executor

    def _redis_available(self) -> bool:
        executor = self._get_executor()
        if executor is None:
            return False
        try:
            return executor.client.ping()
        except Exception as exc:
            logger.debug("redis market driver ping %s: %s", self._market, exc)
            return False

    async def submit_order(self, request: TradeRequest) -> TradeResponse:
        executor = self._get_executor()
        if executor is not None and self._redis_available():
            try:
                response = await executor.submit_order(request)
                if response.status != OrderStatus.PENDING:
                    return response
                if not self._fallback_enabled:
                    return response
            except Exception as exc:
                logger.warning("redis submit %s failed: %s", self._market, exc)

        if self._fallback_enabled:
            return await self._paper.submit_order(request)

        return TradeResponse(
            request_id=request.request_id,
            status=OrderStatus.REJECTED,
            message=f"redis_unavailable:{self._market}",
        )

    async def cancel_order(self, order_id: str, symbol: str) -> TradeResponse:
        executor = self._get_executor()
        if executor is not None and self._redis_available():
            try:
                return await executor.cancel_order(order_id, symbol)
            except Exception as exc:
                logger.warning("redis cancel %s: %s", self._market, exc)
        return await self._paper.cancel_order(order_id, symbol)

    async def get_order_status(self, order_id: str, symbol: str) -> TradeResponse:
        executor = self._get_executor()
        if executor is not None and self._redis_available():
            try:
                return await executor.get_order_status(order_id, symbol)
            except Exception as exc:
                logger.debug("redis status %s: %s", self._market, exc)
        return await self._paper.get_order_status(order_id, symbol)

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        executor = self._get_executor()
        if executor is not None and self._redis_available():
            try:
                return await executor.get_positions(symbol)
            except Exception as exc:
                logger.debug("redis positions %s: %s", self._market, exc)
        return await self._paper.get_positions(symbol)

    async def get_balance(self, asset: str | None = None) -> dict:
        executor = self._get_executor()
        if executor is not None and self._redis_available():
            try:
                return await executor.get_balance(asset)
            except Exception as exc:
                logger.debug("redis balance %s: %s", self._market, exc)
        return await self._paper.get_balance(asset)

    async def health_check(self) -> bool:
        if self._redis_available():
            return True
        return await self._paper.health_check()


__all__ = ["RedisMarketExecutionDriver"]
