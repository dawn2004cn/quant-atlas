"""Execution service ? delegates to the full TradeExecutionPipelineService.

This module is the public interface for trade execution. It delegates all
real work to `TradeExecutionPipelineService`, which runs the Fast Path
chain: Compliance ? Pre-Trade Validation ? Impact ? Audit ? Execute.

All new callers should inject `TradeExecutionPipelineService` directly.
This service is retained for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from app.core.base_service import BaseApplicationService
from app.core.logger import get_logger

logger = get_logger(__name__)


class ExecutionService(BaseApplicationService):
    """Delegating execution service (backward-compatible wrapper).

    Initializes `TradeExecutionPipelineService` lazily so this service can
    be wired without full infrastructure at start-up.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._pipeline: Any = None

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is None:
            from app.modules.execution.services.trade_execution_pipeline_service import (
                TradeExecutionPipelineService,
            )
            self._pipeline = TradeExecutionPipelineService()
            logger.debug("ExecutionService: wired to TradeExecutionPipelineService")
        return self._pipeline

    def execute(
        self,
        *,
        user_id: int,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a trade via the full pipeline.

        Keyword arguments are forwarded to `TradeExecutionPipelineService.execute()`.
        Returns the `PipelineResult` dict.
        """
        pipeline = self._ensure_pipeline()
        result = pipeline.execute(
            user_id=user_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            **kwargs,
        )
        return {
            "ok": result.ok,
            "order_id": result.order_id,
            "stage": result.stage,
            "violations": result.violations,
            "execution": result.execution,
        }

    def validate(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
    ) -> dict[str, Any]:
        """Dry-run validation without execution.

        Returns the validation result without submitting an order.
        """
        from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO

        direction = (
            SignalDirection.BUY
            if action.lower() in ("buy", "long")
            else SignalDirection.SELL
        )
        signal = TradeSignalDTO(
            symbol=symbol.upper(),
            direction=direction,
            price=float(price),
            quantity=int(quantity),
            strategy_id="validation",
        )
        pipeline = self._ensure_pipeline()
        check = pipeline._pre_trade_check(signal, "validate.dry")
        return {
            "valid": check.get("valid", False),
            "reason": check.get("reason", ""),
        }
