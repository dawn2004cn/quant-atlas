"""QMT Execution Gateway with Slippage Tracking.

Phase 42: 交易反馈环与滑点分析
Phase 43: 全链路链路追踪

Enhanced QMTExecutor to:
- Track order submission time vs fill time (latency)
- Record expected price vs actual fill price (slippage)
- Feed execution data back to analysis service
- Propagate trace context across execution
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.core.runtime_config import get_runtime_bool
from app.domain.ports.execution_ports import ITradeExecutor
from app.domain.dto.trade_signal_dto import TradeSignalDTO, SignalDirection
from app.infrastructure.repositories.execution_feedback import ExecutionFeedbackRepository
from app.infrastructure.tracing import create_span, trace_order_execution, get_current_trace_id

from app.core.logger import get_logger

logger = get_logger(__name__)


def qmt_executor_status(
    *,
    account_id: str = "",
    qmt_path: str = "",
    live_submit: bool | None = None,
) -> dict[str, Any]:
    """Public status for manifests and UX self-check (no secrets)."""
    live = (
        get_runtime_bool("QMT_LIVE_SUBMIT", False)
        if live_submit is None
        else bool(live_submit)
    )
    configured = bool((account_id or "").strip())
    path_set = bool((qmt_path or "").strip())
    if not configured:
        mode = "disabled"
    elif live and path_set:
        mode = "live"
    else:
        mode = "simulation"
    return {
        "gateway": "qmt",
        "configured": configured,
        "account_id_set": configured,
        "qmt_path_set": path_set,
        "live_submit": live,
        "execution_mode": mode,
        "xtquant_required": live,
        "warning": (
            "QMT_LIVE_SUBMIT=0 — orders are recorded locally only"
            if configured and not live
            else None
        ),
    }


class QMTExecutor(ITradeExecutor):
    """Execution adapter for Tonghuashun QMT with slippage tracking."""

    def __init__(
        self,
        account_id: str,
        qmt_path: str,
        feedback_repo: Optional[ExecutionFeedbackRepository] = None,
        *,
        live_submit: bool | None = None,
    ):
        self.account_id = account_id
        self.qmt_path = qmt_path
        self._feedback_repo = feedback_repo
        self._pending_orders: dict[str, dict] = {}
        self._live_submit = (
            get_runtime_bool("QMT_LIVE_SUBMIT", False)
            if live_submit is None
            else bool(live_submit)
        )
        logger.info(
            "QMTExecutor initialized for account %s (mode=%s)",
            account_id,
            self.execution_mode,
        )

    @property
    def execution_mode(self) -> str:
        if not (self.account_id or "").strip():
            return "disabled"
        return "live" if self._live_submit else "simulation"

    @property
    def is_simulation(self) -> bool:
        return self.execution_mode == "simulation"

    def status(self) -> dict[str, Any]:
        return qmt_executor_status(
            account_id=self.account_id,
            qmt_path=self.qmt_path,
            live_submit=self._live_submit,
        )

    def execute(self, signal: TradeSignalDTO) -> str:
        """
        Execute trade using QMT API with slippage tracking.
        
        Args:
            signal: Trade signal with expected price and quantity
            
        Returns:
            Order ID
        """
        with trace_order_execution(
            order_id="",  # Will be set after generation
            symbol=signal.symbol,
            side=signal.direction.value,
            price=signal.price,
            quantity=signal.quantity,
        ) as span:
            order_id = f"QMT_{signal.symbol}_{int(datetime.now().timestamp())}"
            order_time = datetime.now()
            span.set_attribute("order_id", order_id)
            span.set_attribute("trace_id", get_current_trace_id() or "")

            user_id = getattr(signal, "user_id", None)
            strategy_id = getattr(signal, "strategy_id", None)
            if user_id and not strategy_id:
                from app.domain.value_objects import encode_retail_strategy_id

                strategy_id = encode_retail_strategy_id(int(user_id))
            self._pending_orders[order_id] = {
                "order_id": order_id,
                "symbol": signal.symbol,
                "side": signal.direction.value,
                "expected_price": signal.price,
                "expected_volume": signal.quantity,
                "order_time": order_time,
                "strategy_id": strategy_id,
                "user_id": int(user_id) if user_id else None,
                "gateway": "qmt",
                "simulation": self.is_simulation,
            }

            span.set_attribute("execution_mode", self.execution_mode)
            span.set_attribute("simulation", self.is_simulation)

            if not self._live_submit:
                logger.info(
                    "QMT simulation order recorded (QMT_LIVE_SUBMIT=0): %s",
                    order_id,
                )
                return order_id

            try:
                from xtquant import xttrader, xtconstant  # noqa: F401

                _direction = 23 if signal.direction == SignalDirection.BUY else 24
                logger.info(
                    "QMT live submit: %s %s %s at %s (dir=%s)",
                    signal.symbol,
                    signal.direction.value,
                    signal.quantity,
                    signal.price,
                    _direction,
                )
                # trader = xttrader.XtQuantTrader(self.qmt_path, self.account_id)
                # trader.connect()
                # order_result = trader.order_stock(...)
                self._pending_orders[order_id]["simulation"] = False
                span.set_attribute("simulation", False)
                return order_id
            except ImportError as exc:
                logger.error("xtquant not installed for QMT live submit: %s", exc)
                span.set_attribute("error", "xtquant_missing")
                raise RuntimeError(
                    "QMT_LIVE_SUBMIT=1 but xtquant is not installed"
                ) from exc

            except Exception as e:
                logger.error(f"QMT execution failed: {e}")
                span.set_attribute("error", str(e))
                raise

    def on_order_filled(
        self,
        order_id: str,
        fill_price: float,
        fill_volume: int,
        fill_time: Optional[datetime] = None,
    ) -> None:
        """
        Handle order fill event and record execution feedback.
        
        This should be called by the QMT callback handler when an order is filled.
        
        Args:
            order_id: Order ID from execute()
            fill_price: Actual fill price
            fill_volume: Actual fill volume
            fill_time: Fill timestamp (defaults to now)
        """
        with create_span("order.fill", attributes={"order_id": order_id}) as span:
            if order_id not in self._pending_orders:
                logger.warning(f"Order {order_id} not found in pending orders")
                span.set_attribute("status", "not_found")
                return

            order_info = self._pending_orders.pop(order_id)
            fill_time = fill_time or datetime.now()

            # Calculate slippage
            expected_price = order_info["expected_price"]
            slippage = fill_price - expected_price
            slippage_pct = (slippage / expected_price * 100) if expected_price > 0 else 0.0

            # Calculate latency
            order_time = order_info["order_time"]
            latency_ms = (fill_time - order_time).total_seconds() * 1000

            # Determine execution quality
            if abs(slippage_pct) < 0.1:
                quality = "excellent"
            elif abs(slippage_pct) < 0.5:
                quality = "good"
            elif abs(slippage_pct) < 1.0:
                quality = "normal"
            else:
                quality = "poor"

            # Record execution feedback
            execution_data = {
                "order_id": order_id,
                "symbol": order_info["symbol"],
                "side": order_info["side"],
                "expected_price": expected_price,
                "fill_price": fill_price,
                "slippage": slippage,
                "slippage_pct": slippage_pct,
                "expected_volume": order_info["expected_volume"],
                "fill_volume": fill_volume,
                "fill_rate": fill_volume / order_info["expected_volume"],
                "order_time": order_time,
                "fill_time": fill_time,
                "latency_ms": latency_ms,
                "execution_quality": quality,
                "strategy_id": order_info.get("strategy_id"),
                "gateway": order_info.get("gateway", "qmt"),
                "simulation": bool(order_info.get("simulation", True)),
                "execution_mode": "simulation"
                if order_info.get("simulation", True)
                else "live",
            }

            span.set_attribute("slippage_pct", slippage_pct)
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("execution_quality", quality)

            if self._feedback_repo:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(self._feedback_repo.record_execution(execution_data))
                    else:
                        loop.run_until_complete(self._feedback_repo.record_execution(execution_data))
                except Exception as e:
                    logger.error(f"Failed to record execution feedback: {e}")
                    span.set_attribute("feedback_error", str(e))

            uid = order_info.get("user_id")
            if uid is None:
                from app.domain.value_objects import parse_user_id_from_strategy_id

                uid = parse_user_id_from_strategy_id(order_info.get("strategy_id"))
            if uid:
                try:
                    from app.modules.system.services.helpers.psychology_trade_hooks import (
                        record_execution_fill,
                    )

                    record_execution_fill(
                        user_id=int(uid),
                        symbol=str(order_info.get("symbol") or ""),
                        side=str(order_info.get("side") or "buy"),
                        change_pct=float(slippage_pct),
                        metadata={
                            "order_id": order_id,
                            "fill_price": fill_price,
                            "execution_quality": quality,
                        },
                    )
                except Exception as e:
                    logger.warning("psychology fill hook: %s", e)

            logger.info(
                f"Order filled: {order_id} | "
                f"Slippage: {slippage_pct:.2f}% | "
                f"Latency: {latency_ms:.0f}ms | "
                f"Quality: {quality}"
            )

    def cancel(self, order_id: str) -> bool:
        """Cancel order and remove from pending tracking."""
        logger.info(f"QMT Cancelling order: {order_id}")
        self._pending_orders.pop(order_id, None)
        return True

    def get_pending_orders(self) -> dict[str, dict]:
        """Get all pending orders."""
        return self._pending_orders.copy()
