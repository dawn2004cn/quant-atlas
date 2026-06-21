from __future__ import annotations

import logging
from typing import Any, Optional
from dataclasses import dataclass

from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode

logger = logging.getLogger(__name__)

@dataclass
class FastPathResult:
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0

class FastPathOrchestrator(BaseApplicationService):
    """
    The Fast Path Orchestrator is the 'reflex arc' of the system.
    It is strictly forbidden from calling any LLM or slow-latency services.
    
    Flow: Parameter Fetch -> Pre-trade Validation -> Hard Risk Guard -> Execution Gateway.
    """

    def __init__(
        self,
        pre_trade_validator: Any,
        risk_guard: Any,
        execution_gateway: Any,
        parameter_store: Any,
    ) -> None:
        super().__init__()
        self._validator = pre_trade_validator
        self._risk_guard = risk_guard
        self._gateway = execution_gateway
        self._param_store = parameter_store

    def execute_trade(self, trade_request: Any) -> FastPathResult:
        """
        High-speed execution path. 
        Pulls pre-computed parameters from the ParameterStore.
        """
        import time
        start = time.perf_counter()
        
        symbol = trade_request.symbol
        
        try:
            # 1. Fetch pre-computed risk parameters (Fast Path)
            # e.g., current ATR-based stop distance computed by Slow Path
            stop_distance = self._param_store.get_parameter(symbol, "stop_distance", default=0.02)
            
            # 2. Hard Validation (Minimal overhead)
            if not self._validator.validate(trade_request, stop_distance=stop_distance):
                return FastPathResult(success=False, error="Pre-trade validation failed")
            
            # 3. Hard Risk Guard (Slippage, Position Limit, etc.)
            if not self._risk_guard.check_limits(trade_request):
                return FastPathResult(success=False, error="Risk limit exceeded")
            
            # 4. Atomic Execution
            order_id = self._gateway.send_order(trade_request)
            
            duration = (time.perf_counter() - start) * 1000
            return FastPathResult(success=True, order_id=order_id, latency_ms=duration)
            
        except Exception as e:
            logger.error("FastPath Execution Critical Failure: %s", e)
            return FastPathResult(success=False, error=str(e))
