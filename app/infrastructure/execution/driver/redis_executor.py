from __future__ import annotations

"""Redis Stream Executor - 基于 Redis Stream 的异步交易执行网关。"""

import asyncio
import json
import logging
import time

from app.core.runtime_config import get_runtime

from .protocol import (
    ExecutionGateway,
    OrderStatus,
    TradeRequest,
    TradeResponse,
)
from .redis_executor_codec import (
    decode_trade_request,
    decode_trade_response,
    encode_cancel_payload,
    encode_trade_request,
    order_status_key,
    result_key_for,
)
from .redis_stream_connection import RedisStreamConnection

logger = logging.getLogger(__name__)


class RedisStreamExecutor(ExecutionGateway):
    """基于 Redis Stream 的交易执行器。

    1. submit_order: 写入 execution_queue
    2. 轮询 result_stream 等待 worker 回写
    3. worker (独立进程) 消费队列并调用 process_result
    """

    def __init__(
        self,
        redis_url: str = get_runtime("REDIS_URL", ""),
        queue_name: str = "execution_queue",
        result_prefix: str = "execution_result:",
        timeout: float = 30.0,
    ) -> None:
        self._result_prefix = result_prefix
        self._timeout = timeout
        self._conn = RedisStreamConnection(redis_url, queue_name)

    @property
    def client(self):
        return self._conn.client

    async def connect(self) -> bool:
        try:
            self._conn.ping()
            self._conn.ensure_consumer_group()
            logger.info("RedisStreamExecutor connected: %s", self._conn.redis_url)
            return True
        except Exception as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            return False

    async def submit_order(self, request: TradeRequest) -> TradeResponse:
        payload = encode_trade_request(request)
        msg_id = self.client.xadd(
            self._conn.queue_name,
            {"payload": payload, "request_id": request.request_id},
        )
        logger.info("Order submitted: %s, msg_id: %s", request.request_id, msg_id)

        result_key = result_key_for(self._result_prefix, request.request_id)
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            result = self.client.get(result_key)
            if result:
                return decode_trade_response(result)
            await asyncio.sleep(0.1)

        logger.warning("Order timeout: %s", request.request_id)
        return TradeResponse(
            request_id=request.request_id,
            status=OrderStatus.PENDING,
            message="Order execution timeout",
        )

    async def cancel_order(self, order_id: str, symbol: str) -> TradeResponse:
        payload = encode_cancel_payload(order_id, symbol)
        self.client.xadd(self._conn.queue_name, {"payload": payload})
        return TradeResponse(
            request_id=f"cancel_{order_id}",
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            message="Cancel request submitted",
        )

    async def get_order_status(self, order_id: str, symbol: str) -> TradeResponse:
        key = order_status_key(order_id)
        status_data = self.client.get(key)
        if status_data:
            return decode_trade_response(status_data)
        return TradeResponse(
            request_id=f"query_{order_id}",
            order_id=order_id,
            status=OrderStatus.PENDING,
            message="Order status unknown",
        )

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        data = self.client.get("positions")
        if not data:
            return []
        positions: list[dict] = json.loads(data)
        if symbol:
            return [p for p in positions if p.get("symbol") == symbol]
        return positions

    async def get_balance(self, asset: str | None = None) -> dict:
        data = self.client.get("balance")
        if not data:
            return {}
        balance: dict = json.loads(data)
        if asset:
            return balance.get(asset, {"free": 0, "locked": 0})
        return balance

    async def health_check(self) -> bool:
        try:
            self._conn.ping()
            return True
        except Exception:
            return False

    def process_result(self, request_id: str, response_data: dict) -> None:
        response = TradeResponse.from_dict(response_data)
        if response.order_id:
            self.client.setex(
                order_status_key(response.order_id),
                3600,
                json.dumps(response.to_dict()),
            )
        result_key = result_key_for(self._result_prefix, request_id)
        self.client.setex(result_key, 60, json.dumps(response_data))

    def start_worker_loop(self) -> None:
        while True:
            try:
                messages = self.client.xreadgroup(
                    self._conn.consumer_group,
                    "worker_1",
                    {self._conn.queue_name: ">"},
                    count=1,
                    block=5000,
                )
                if not messages:
                    continue
                for _stream, msgs in messages:
                    for msg_id, msg_data in msgs:
                        payload = msg_data.get("payload", "{}")
                        request_id = msg_data.get("request_id", "")
                        try:
                            req = decode_trade_request(payload)
                            result = self._simulate_execute(req)
                            self.process_result(request_id, result.to_dict())
                        except Exception as exc:
                            logger.error("Execute failed: %s", exc, exc_info=True)
                            error_resp = TradeResponse(
                                request_id=request_id,
                                status=OrderStatus.REJECTED,
                                message=str(exc),
                            )
                            self.process_result(request_id, error_resp.to_dict())
                        self.client.xack(
                            self._conn.queue_name,
                            self._conn.consumer_group,
                            msg_id,
                        )
            except Exception as exc:
                logger.error("Worker loop error: %s", exc, exc_info=True)
                time.sleep(1)

    def _simulate_execute(self, request: TradeRequest) -> TradeResponse:
        return TradeResponse(
            request_id=request.request_id,
            order_id=f"sim_{request.request_id}",
            status=OrderStatus.FILLED,
            filled_amount=request.amount,
            filled_price=request.price,
            message="Simulated fill",
        )
