from __future__ import annotations
"""Application service for managing trading bots via ExecutionGateway drivers."""

import threading
from collections.abc import Callable
from typing import Any

from app.core.base_service import BaseApplicationService
from app.application.trading.bot_engine import BotEngine
from app.domain.dto.trading_dto import BotActionResponseDTO, BotDetailDTO, BotStatusDTO
from app.domain.execution.driver_protocol import ExecutionGateway
from app.domain.ports import TradeRepository, TradingBotProvider
from app.domain.strategy import BaseStrategy
from app.infrastructure.execution.driver_registry import resolve_bot_execution_gateway


class TradingBotService(BaseApplicationService, TradingBotProvider):
    """Orchestrate Freqtrade-style bots through ExecutionGateway (not ExchangePort)."""

    def __init__(
        self,
        repository: TradeRepository,
        strategy_factory: object,
        *,
        execution_gateway: ExecutionGateway | None = None,
        execution_gateway_factory: Callable[[dict[str, Any]], ExecutionGateway] | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._strategy_factory = strategy_factory
        self._default_gateway = execution_gateway
        self._gateway_factory = execution_gateway_factory or resolve_bot_execution_gateway
        self._bots: dict[str, BotEngine] = {}
        self._threads: dict[str, threading.Thread] = {}

    def _resolve_gateway(self, bot_config: dict[str, Any]) -> ExecutionGateway:
        if self._default_gateway is not None:
            return self._default_gateway
        return self._gateway_factory(bot_config)

    def start(self, strategy_name: str, symbols: list[str], config: dict[str, Any] | None = None) -> None:
        if strategy_name in self._bots:
            raise ValueError(f"Bot with strategy {strategy_name} is already running.")

        bot_config: dict[str, Any] = {
            "strategy_name": strategy_name,
            "symbols": symbols,
            "max_open_trades": 5,
            "stake_amount": 100.0,
            "loop_interval": 60,
            "exchange_id": "paper_cn",
            "market": "CN",
            "execution_mode": "paper",
        }
        if config:
            bot_config.update(config)

        strategy: BaseStrategy = self._strategy_factory(strategy_name)
        gateway = self._resolve_gateway(bot_config)
        bot = BotEngine(
            repository=self._repository,
            strategy=strategy,
            config=bot_config,
            execution_gateway=gateway,
        )
        self._bots[strategy_name] = bot
        self._logger.info(
            "Starting bot %s via ExecutionGateway backend=%s",
            strategy_name,
            getattr(gateway, "describe", lambda: {})() if hasattr(gateway, "describe") else "gateway",
        )

        thread = threading.Thread(target=bot.start, daemon=True)
        self._threads[strategy_name] = thread
        thread.start()

    def stop(self, strategy_name: str | None = None) -> None:
        if strategy_name:
            if strategy_name in self._bots:
                self._bots[strategy_name].stop()
                del self._bots[strategy_name]
                del self._threads[strategy_name]
        else:
            for bot in self._bots.values():
                bot.stop()
            self._bots.clear()
            self._threads.clear()

    def get_status(self) -> BotStatusDTO:
        return BotStatusDTO(
            running_bots=list(self._bots.keys()),
            open_trades_count=len(self._repository.get_open_trades()),
        )

    def start_bot(self, strategy_name: str, symbol: str) -> BotActionResponseDTO:
        self.start(strategy_name, [symbol])
        return BotActionResponseDTO(status="started", strategy=strategy_name, symbol=symbol)

    def stop_bot(self, strategy_name: str, symbol: str) -> BotActionResponseDTO:
        self.stop(strategy_name)
        return BotActionResponseDTO(status="stopped", strategy=strategy_name, symbol=symbol)

    def get_bot_status(self, strategy_name: str, symbol: str) -> BotDetailDTO:
        return BotDetailDTO(
            running=strategy_name in self._bots,
            strategy=strategy_name,
            symbol=symbol,
        )
