"""Generated proto stubs — compile from gateway/proto/trade_execution.proto."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── In-memory stub (no protobuf dependency needed at runtime) ──

@dataclass
class RiskCheck:
    check: str = ""
    detail: str = ""
    passed: bool = False

@dataclass
class OrderResponse:
    order_id: str = ""
    accepted: bool = False
    reason: str = ""
    state: str = ""
    failures: list[RiskCheck] = field(default_factory=list)
    gateway_version: str = ""

class TradeExecutionStub:
    """In-process stub matching the Go gateway's gRPC contract.

    Falls back to local Python PreTradeValidator when gRPC is unavailable.
    """
    def __init__(self, use_grpc: bool = False, grpc_target: str = "localhost:9090"):
        self._grpc = use_grpc
        self._target = grpc_target
        self._channel = None
        self._client = None
        self._orders_processed = 0
        self._orders_failed = 0

    def _ensure_grpc(self) -> bool:
        if self._client is not None:
            return True
        if not self._grpc:
            return False
        try:
            import grpc  # type: ignore[import-untyped]
            from . import trade_execution_pb2_grpc  # type: ignore[import-untyped]
            self._channel = grpc.insecure_channel(self._target)
            self._client = trade_execution_pb2_grpc.TradeExecutionStub(self._channel)
            return True
        except Exception as exc:
            logger.warning("[gateway] gRPC unavailable, using local fallback: %s", exc)
            self._grpc = False
            return False

    def submit_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        strategy_id: str = "",
        user_id: str = "",
        max_trade_amount: float = 0.0,
        max_position: int = 0,
        dry_run: bool = False,
        metadata: dict[str, str] | None = None,
        local_fallback: Any = None,
    ) -> OrderResponse:
        if self._ensure_grpc():
            try:
                from . import trade_execution_pb2
                req = trade_execution_pb2.OrderRequest(
                    order_id=order_id, symbol=symbol, side=side,
                    price=price, quantity=quantity,
                    strategy_id=strategy_id, user_id=user_id,
                    max_trade_amount=max_trade_amount, max_position=max_position,
                    dry_run=dry_run, metadata=metadata or {},
                )
                resp = self._client.SubmitOrder(req, timeout=5.0)
                self._orders_processed += 1
                return OrderResponse(
                    order_id=resp.order_id,
                    accepted=resp.accepted,
                    reason=resp.reason,
                    state=resp.state,
                    failures=[RiskCheck(c.check, c.detail, c.passed) for c in resp.failures],
                    gateway_version=resp.gateway_version,
                )
            except Exception as exc:
                self._orders_failed += 1
                logger.error("[gateway] gRPC call failed, falling back: %s", exc)

        return self._local_submit(
            order_id, symbol, side, price, quantity,
            strategy_id, user_id, max_trade_amount, max_position, dry_run,
            metadata, local_fallback,
        )

    def _local_submit(self, order_id, symbol, side, price, quantity,
                      strategy_id, user_id, max_trade_amount, max_position, dry_run,
                      metadata, fallback) -> OrderResponse:
        if fallback and hasattr(fallback, "validate"):
            from app.domain.dto.trade_signal_dto import TradeSignalDTO, SignalDirection
            signal = TradeSignalDTO(
                symbol=symbol,
                direction=SignalDirection(side.upper()),
                price=price,
                quantity=quantity,
                strategy_id=strategy_id,
                user_id=int(user_id) if user_id else None,
            )
            ok = fallback.validate(signal)
            self._orders_processed += 1
            if ok:
                return OrderResponse(order_id=order_id, accepted=True, state="accepted", reason="local validate OK")
            return OrderResponse(order_id=order_id, accepted=False, state="rejected", reason="local validate failed")
        self._orders_processed += 1
        return OrderResponse(order_id=order_id, accepted=True, state="accepted", reason="no fallback validator")

    @property
    def is_grpc_connected(self) -> bool:
        return self._client is not None and self._channel is not None

    def close(self) -> None:
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                logger.debug("Gateway channel close failed (expected on shutdown)")
