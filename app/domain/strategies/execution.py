from __future__ import annotations
"""Strategy execution engine."""


from dataclasses import dataclass
from datetime import datetime

from app.core.logger import get_logger
from app.domain.strategies.base import (
    BaseStrategy,
    StrategySignal,
    StrategyResult,
    StrategyRegistry,
)

logger = get_logger(__name__)


class StrategyExecutor:
    """Engine for executing trading strategies."""

    def __init__(self):
        self._active_strategies: dict[str, BaseStrategy] = {}
        logger.info("StrategyExecutor initialized")

    def add_strategy(self, name: str, strategy: BaseStrategy):
        """Add an active strategy."""
        self._active_strategies[name] = strategy
        logger.info(f"Added strategy: {name}")

    def remove_strategy(self, name: str):
        """Remove an active strategy."""
        if name in self._active_strategies:
            del self._active_strategies[name]
            logger.info(f"Removed strategy: {name}")

    def execute_all(self, data: dict[str, Any]) -> StrategyResult:
        """Execute all active strategies."""
        all_signals = []
        errors = []

        for name, strategy in self._active_strategies.items():
            try:
                if not strategy.enabled:
                    continue

                result = strategy.analyze(data)
                all_signals.extend(result.signals)
                errors.extend(result.errors)

            except Exception as e:
                logger.error(f"Strategy '{name}' execution failed: {e}")
                errors.append(f"{name}: {str(e)}")

        return StrategyResult(
            signals=all_signals,
            errors=errors,
            metrics={"strategy_count": len(self._active_strategies)},
        )

    def execute_single(self, strategy_name: str, params: dict, data: dict[str, Any]) -> StrategyResult:
        """Execute a single strategy by name."""
        strategy = StrategyRegistry.get(strategy_name, params)
        return strategy.analyze(data)

    def list_active_strategies(self) -> list[str]:
        """List active strategy names."""
        return list(self._active_strategies.keys())

    def enable_strategy(self, name: str):
        """Enable a strategy."""
        if name in self._active_strategies:
            self._active_strategies[name].enabled = True

    def disable_strategy(self, name: str):
        """Disable a strategy."""
        if name in self._active_strategies:
            self._active_strategies[name].enabled = False


@dataclass
class ExecutionOrder:
    """Order to be executed."""
    signal: StrategySignal
    order_type: str  # market, limit
    status: str = "pending"  # pending, submitted, filled, cancelled
    order_id: str = ""
    filled_price: float = 0.0
    filled_quantity: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SignalDispatcher:
    """Dispatcher for routing signals to execution."""

    def __init__(self, executor: StrategyExecutor | None = None):
        self._executor = executor or StrategyExecutor()
        self._execution_handlers: list[callable] = []
        logger.info("SignalDispatcher initialized")

    def register_handler(self, handler: callable):
        """Register a signal execution handler."""
        self._execution_handlers.append(handler)

    async def dispatch(self, signal: StrategySignal) -> ExecutionOrder:
        """Dispatch a signal to execution."""
        order = ExecutionOrder(signal=signal, order_type="market")

        for handler in self._execution_handlers:
            try:
                await handler(signal)
                order.status = "submitted"
            except Exception as e:
                logger.error(f"Handler execution failed: {e}")
                order.status = "failed"

        return order

    def dispatch_batch(self, signals: list[StrategySignal]) -> list[ExecutionOrder]:
        """Dispatch multiple signals."""
        return [self._create_order(s) for s in signals]

    def _create_order(self, signal: StrategySignal) -> ExecutionOrder:
        """Create an execution order from a signal."""
        return ExecutionOrder(signal=signal, order_type="limit" if signal.target_price else "market")


_executor = StrategyExecutor()
_dispatcher = SignalDispatcher(_executor)


def get_strategy_executor() -> StrategyExecutor:
    """Get global strategy executor."""
    return _executor


def get_signal_dispatcher() -> SignalDispatcher:
    """Get global signal dispatcher."""
    return _dispatcher


__all__ = [
    "StrategyExecutor",
    "SignalDispatcher",
    "ExecutionOrder",
    "get_strategy_executor",
    "get_signal_dispatcher",
]