from __future__ import annotations
"""Borderless execution orchestration (Quant Atlas 9.0 Step Two)."""

import asyncio
import logging
import uuid
from typing import Any

from app.core.event_bus import emit_trade_executed
from app.core.mesh.distributed_event_bus import get_distributed_event_bus
from app.core.runtime_config import get_runtime, get_runtime_bool
from app.domain.execution.driver_protocol import OrderStatus, TradeResponse
from app.domain.execution.execution_schema import BorderlessOrderRequest, ExecutionManifest
from app.domain.execution.market_router import resolve_execution_route
from app.infrastructure.execution.borderless_router import BorderlessExecutionRouter
from app.infrastructure.execution.driver.order_manager import OrderManager, OrderState
from app.infrastructure.execution.driver_registry import build_borderless_router
from app.infrastructure.execution.drivers.paper_driver import build_trade_request_from_borderless

logger = logging.getLogger(__name__)


class BorderlessExecutionService:
    """Cross-market order routing with audit lineage and optional mesh fan-out."""

    def __init__(
        self,
        *,
        router: BorderlessExecutionRouter | None = None,
        order_manager: OrderManager | None = None,
    ) -> None:
        self._router = router or self._build_default_router()
        self._orders = order_manager or OrderManager()

    @staticmethod
    def _build_default_router() -> BorderlessExecutionRouter:
        return build_borderless_router()

    def get_manifest(self) -> dict[str, Any]:
        mode = get_runtime("EXECUTION_DEFAULT_MODE", "paper")
        enabled = get_runtime_bool("BORDERLESS_EXECUTION_ENABLED", True)
        drivers = self._router.list_drivers()
        manifest = ExecutionManifest(
            enabled=enabled,
            default_mode=mode,
            markets=["CN", "US", "HK", "CRYPTO"],
            drivers=drivers,
            mesh_linked=get_distributed_event_bus() is not None,
        )
        out: dict[str, Any] = {"ok": True, **manifest.model_dump(mode="json")}
        try:
            from app.config import get_settings
            from app.infrastructure.execution.qmt_executor import qmt_executor_status

            qmt = get_settings().qmt
            out["qmt"] = qmt_executor_status(
                account_id=qmt.account_id or "",
                qmt_path=qmt.qmt_path or "",
            )
        except Exception as exc:
            logger.debug("qmt manifest probe failed: %s", exc)
            out["qmt"] = {"gateway": "qmt", "configured": False, "execution_mode": "disabled"}
        return out

    def preview_route(self, symbol: str, *, market: str | None = None) -> dict[str, Any]:
        route = self._router.preview_route(symbol, market_hint=market)
        return {"ok": True, "route": route.model_dump(mode="json")}

    def submit_order(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            req = BorderlessOrderRequest.model_validate(body)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"invalid_request:{exc}"}

        if not str(req.provenance_id or "").strip():
            req.provenance_id = f"prov_{uuid.uuid4().hex}"

        route = resolve_execution_route(
            req.symbol,
            market_hint=req.market,
            mode=str(req.metadata.get("mode") or get_runtime("EXECUTION_DEFAULT_MODE", "paper")),
            exchange_hint=req.exchange,
        )
        trade_req = build_trade_request_from_borderless(
            route_market=route.market.value,
            route_exchange=route.exchange,
            symbol=route.symbol,
            side=req.side,
            order_type=req.order_type,
            amount=req.amount,
            quantity=req.quantity,
            price=req.price,
            provenance_id=req.provenance_id,
            client_order_id=req.client_order_id,
            metadata=req.metadata,
        )

        try:
            response = asyncio.run(self._router.submit_order(trade_req))
        except KeyError as exc:
            return {"ok": False, "error": str(exc), "route": route.model_dump(mode="json")}
        except Exception as exc:  # noqa: BLE001
            logger.warning("borderless submit failed: %s", exc)
            return {"ok": False, "error": str(exc)}

        self._record_order(trade_req.request_id, response, route.model_dump(mode="json"))
        self._emit_events(req, route, response)
        return {
            "ok": response.is_success(),
            "route": route.model_dump(mode="json"),
            "response": response.to_dict(),
            "provenance_id": req.provenance_id,
        }

    def get_order_status(self, order_id: str, *, symbol: str = "") -> dict[str, Any]:
        sym = symbol or "600519"
        try:
            response = asyncio.run(self._router.get_order_status(order_id, sym))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "response": response.to_dict()}

    def list_recent_orders(self, *, limit: int = 20) -> dict[str, Any]:
        records = self._orders.get_history(limit=limit)
        return {"ok": True, "orders": records, "count": len(records)}

    def _record_order(self, request_id: str, response: TradeResponse, route: dict[str, Any]) -> None:
        state = OrderState.FILLED if response.status == OrderStatus.FILLED else OrderState.SUBMITTED
        if response.status == OrderStatus.REJECTED:
            state = OrderState.REJECTED
        self._orders.create(
            request_id=request_id,
            order_id=response.order_id or request_id,
            symbol=route.get("symbol", ""),
            side="buy",
            amount=response.filled_amount or 0,
            price=response.filled_price or 0,
        )
        self._orders.update_state(
            response.order_id or request_id,
            state,
            filled_amount=response.filled_amount,
            filled_price=response.filled_price,
            error=None if response.is_success() else response.message,
        )

    def _emit_events(
        self,
        req: BorderlessOrderRequest,
        route: Any,
        response: TradeResponse,
    ) -> None:
        if not response.is_success() or response.status != OrderStatus.FILLED:
            return
        user_id = str(req.user_id or req.metadata.get("user_id") or "system")
        qty = float(response.filled_amount or req.quantity or req.amount or 0)
        price = float(response.filled_price or req.price or 0)
        try:
            emit_trade_executed(
                user_id=user_id,
                symbol=route.symbol,
                action=req.side.lower(),
                quantity=qty,
                price=price,
                provenance_id=req.provenance_id,
                market=route.market.value,
                source="borderless_execution",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("borderless emit_trade_executed: %s", exc)

        mesh = get_distributed_event_bus()
        if mesh is not None:
            mesh.publish_local_event(
                "TradeExecutedEvent",
                {
                    "user_id": user_id,
                    "symbol": route.symbol,
                    "market": route.market.value,
                    "action": req.side.lower(),
                    "quantity": qty,
                    "price": price,
                    "provenance_id": req.provenance_id,
                    "order_id": response.order_id,
                },
            )


__all__ = ["BorderlessExecutionService"]
