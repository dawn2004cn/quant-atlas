from typing import Any
from app.domain.strategies.base import BaseStrategy, StrategySignal
from app.core.event_bus import get_event_bus
from app.modules.system.services.helpers.async_market_access import get_standalone_async_market_provider

class Engine:
    """Thin engine that drives a strategy via market ticks."""

    def __init__(self, strategy_cls: type[BaseStrategy], settings: dict[str, Any]):
        self.strategy = strategy_cls(settings)
        self.bus = get_event_bus()
        # subscribe to market tick events
        self.bus.subscribe("market_tick", self._handle_tick)

    def _handle_tick(self, data: dict):  # type: ignore[arg-type]
        # Strategy may produce multiple signals
        signals: list[StrategySignal] = self.strategy.on_market_tick(data)
        for s in signals:
            # publish each signal so other system parts can react
            self.bus.publish("strategy_signal", s.dict())

    async def start(self):
        # Connect to market provider and rebroadcast ticks onto event bus
        provider = get_standalone_async_market_provider()
        await provider.subscribe(self.bus)
