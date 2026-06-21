from __future__ import annotations
"""CCXT implementation of ExchangePort."""


from typing import Any
import ccxt
from datetime import datetime

from app.core.circuit_breaker import CircuitBreakerOpenError, CircuitBreakerRegistry, CircuitBreakerConfig
from app.domain.ports import ExchangePort
from app.domain.trading_entities import Order


class CCXTExchangeAdapter(ExchangePort):
    def __init__(self, exchange_id: str, config: dict[str, Any] | None = None):
        self._exchange_id = exchange_id
        self._config = config or {}
        exchange_class = getattr(ccxt, exchange_id)
        self._exchange = exchange_class(self._config)
        self._breaker = CircuitBreakerRegistry.get(
            f"ccxt_{exchange_id}",
            CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
        )

    def _degraded_empty_ohlcv(self) -> list[dict[str, Any]]:
        try:
            from app.core.middleware.degraded_context import mark_system_degraded

            mark_system_degraded(f"ccxt_{self._exchange_id}")
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return []

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        try:
            return self._breaker.call(self._fetch_ohlcv, symbol, timeframe, limit)
        except CircuitBreakerOpenError:
            return self._degraded_empty_ohlcv()

    def _fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        ohlcv = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return [
            {
                "timestamp": x[0],
                "open": x[1],
                "high": x[2],
                "low": x[3],
                "close": x[4],
                "volume": x[5],
                "date": datetime.fromtimestamp(x[0] / 1000),
            }
            for x in ohlcv
        ]

    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
    ) -> Order:
        try:
            ccxt_order = self._breaker.call(
                self._exchange.create_order,
                symbol,
                order_type,
                side,
                amount,
                price,
            )
        except CircuitBreakerOpenError:
            from app.core.middleware.degraded_context import mark_system_degraded

            mark_system_degraded(f"ccxt_{self._exchange_id}")
            raise
        return self._map_ccxt_order(ccxt_order)

    def get_order(self, order_id: str, symbol: str) -> Order:
        try:
            ccxt_order = self._breaker.call(self._exchange.fetch_order, order_id, symbol)
        except CircuitBreakerOpenError:
            from app.core.middleware.degraded_context import mark_system_degraded


            mark_system_degraded(f"ccxt_{self._exchange_id}")
            raise
        return self._map_ccxt_order(ccxt_order)

    def _map_ccxt_order(self, ccxt_order: dict[str, Any]) -> Order:
        return Order(
            order_id=str(ccxt_order["id"]),
            ft_pair=ccxt_order["symbol"],
            ft_order_side=ccxt_order["side"],
            ft_is_open=ccxt_order["status"] == "open",
            ft_amount=ccxt_order["amount"],
            ft_price=ccxt_order["price"],
            status=ccxt_order["status"],
            symbol=ccxt_order["symbol"],
            order_type=ccxt_order["type"],
            side=ccxt_order["side"],
            filled=ccxt_order.get("filled", 0.0),
            remaining=ccxt_order.get("remaining"),
            cost=ccxt_order.get("cost"),
            order_date=datetime.fromtimestamp(ccxt_order["timestamp"] / 1000) if ccxt_order.get("timestamp") else None,
            order_filled_date=None,  # CCXT doesn't always provide this directly
        )
