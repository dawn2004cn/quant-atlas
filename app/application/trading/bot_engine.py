from __future__ import annotations

"""Core bot loop logic (Freqtrade port) — ExecutionGateway only."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.execution.driver_protocol import ExecutionGateway, OrderSide, OrderType, TradeRequest
from app.domain.ports import TradeRepository
from app.domain.strategy import BaseStrategy
from app.domain.trading_entities import Trade
from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
from app.modules.system.services.helpers.tracing_access import create_span

logger = get_logger(__name__)


class BotEngine:
    def __init__(
        self,
        repository: TradeRepository,
        strategy: BaseStrategy,
        config: dict[str, Any],
        *,
        execution_gateway: ExecutionGateway,
    ) -> None:
        self._repository = repository
        self._strategy = strategy
        self._config = config
        self._execution_gateway = execution_gateway
        self._is_running = False
        self._max_open_trades = config.get("max_open_trades", 5)
        self._stake_amount = config.get("stake_amount", 100.0)

    def run_once(self) -> None:
        with create_span("bot.run_once", attributes={"max_open_trades": self._max_open_trades}) as span:
            logger.info("Bot loop iteration started.")
            symbols = self._config.get("symbols", [])
            open_trades = self._repository.get_open_trades()
            span.set_attribute("open_trades_count", len(open_trades))

            for trade in open_trades:
                self._check_and_execute_exit(trade)

            if len(self._repository.get_open_trades()) < self._max_open_trades:
                for symbol in symbols:
                    if any(t.pair == symbol for t in self._repository.get_open_trades()):
                        continue
                    self._check_and_execute_entry(symbol)

    def _get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[dict]:
        del timeframe
        provider = get_market_data_provider()
        market = MarketCode(str(self._config.get("market") or "CN"))
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=max(limit, 30))).strftime("%Y-%m-%d")
        return provider.get_stock_history(symbol, market, start, end) or []

    def _check_and_execute_entry(self, symbol: str) -> None:
        with create_span("bot.check_entry", attributes={"symbol": symbol}) as span:
            ohlcv = self._get_ohlcv(symbol, self._strategy.timeframe, limit=100)
            if not ohlcv:
                logger.warning("No OHLCV data for %s", symbol)
                span.set_attribute("status", "no_data")
                return

            df = pd.DataFrame(ohlcv)
            df = self._strategy.populate_indicators(df, {"pair": symbol})
            df = self._strategy.populate_entry_trend(df, {"pair": symbol})

            last_row = df.iloc[-1]
            if last_row.get("enter_long", 0) == 1:
                logger.info("Entry signal found for %s", symbol)
                span.set_attribute("signal", "enter_long")
                price = float(last_row["close"])
                amount = self._stake_amount / price
                asyncio.run(self._execute_entry_via_driver(symbol, price, amount))

    async def _execute_entry_via_driver(self, symbol: str, price: float, amount: float) -> None:
        with create_span("bot.execute_entry_driver", attributes={"symbol": symbol, "price": price}) as span:
            request = TradeRequest(
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                amount=amount,
                price=price,
                exchange=self._config.get("exchange_id", "paper_cn"),
                metadata={"strategy": self._strategy.__class__.__name__, "action": "entry"},
            )
            response = await self._execution_gateway.submit_order(request)
            if response.is_success():
                logger.info("Entry order filled: %s", response.order_id)
                span.set_attribute("order_id", response.order_id)
                trade = Trade(
                    exchange=self._config.get("exchange_id", "unknown"),
                    pair=symbol,
                    is_open=True,
                    open_date=datetime.now(),
                    open_rate=response.filled_price or price,
                    stake_amount=self._stake_amount,
                    amount=response.filled_amount or amount,
                    strategy=self._strategy.__class__.__name__,
                    stop_loss=price * (1 + self._strategy.stoploss),
                )
                trade_id = self._repository.save_trade(trade)
                logger.info("Trade saved: %s", trade_id)
                span.set_attribute("trade_id", trade_id)
            else:
                logger.warning("Entry order failed: %s", response.message)
                span.set_attribute("status", "failed")
                span.set_attribute("error", response.message)

    def _check_and_execute_exit(self, trade: Trade) -> None:
        with create_span("bot.check_exit", attributes={"trade_id": trade.id, "pair": trade.pair}) as span:
            ohlcv = self._get_ohlcv(trade.pair, self._strategy.timeframe, limit=1)
            if not ohlcv:
                span.set_attribute("status", "no_data")
                return
            current_rate = float(ohlcv[-1]["close"])
            current_time = time.time()

            exit_reason = None
            if self._strategy.check_roi(trade, current_rate, current_time):
                exit_reason = "roi"
            elif self._strategy.check_stoploss(trade, current_rate):
                exit_reason = "stoploss"

            if exit_reason:
                logger.info("Exit condition met for %s: %s", trade.pair, exit_reason)
                span.set_attribute("exit_reason", exit_reason)
                asyncio.run(self._execute_exit_via_driver(trade, current_rate, exit_reason))

    async def _execute_exit_via_driver(self, trade: Trade, current_rate: float, exit_reason: str) -> None:
        with create_span(
            "bot.execute_exit_driver",
            attributes={"trade_id": trade.id, "exit_reason": exit_reason},
        ) as span:
            request = TradeRequest(
                symbol=trade.pair,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                amount=trade.amount,
                price=current_rate,
                exchange=trade.exchange,
                metadata={"strategy": trade.strategy, "action": "exit", "reason": exit_reason},
            )
            response = await self._execution_gateway.submit_order(request)
            if response.is_success():
                logger.info("Exit order filled: %s", response.order_id)
                span.set_attribute("order_id", response.order_id)
                trade.is_open = False
                trade.close_date = datetime.now()
                trade.close_rate = response.filled_price or current_rate
                trade.exit_reason = exit_reason
                trade.close_profit = trade.calc_profit_ratio(trade.close_rate)
                trade.close_profit_abs = (trade.close_rate - trade.open_rate) * trade.amount
                self._repository.save_trade(trade)
                span.set_attribute("status", "success")
            else:
                logger.warning("Exit order failed: %s", response.message)
                span.set_attribute("status", "failed")
                span.set_attribute("error", response.message)

    def start(self) -> None:
        self._is_running = True
        while self._is_running:
            try:
                self.run_once()
            except Exception as exc:
                logger.error("Error in bot loop: %s", exc)
            time.sleep(self._config.get("loop_interval", 60))

    def stop(self) -> None:
        self._is_running = False
