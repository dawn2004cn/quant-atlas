from __future__ import annotations
"""Trading Service with Transactional Outbox Integration.

This module demonstrates how to use the Transactional Outbox Pattern
to ensure reliable event publishing for trading operations.

The key insight is that within a single DB transaction, we:
1. Save the trade/order data
2. Write an event to the outbox table

This guarantees that either both succeed or both fail.
"""


import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select


from app.core.logger import get_logger

logger = get_logger(__name__)


class TradingService:
    """Trading service with transactional outbox support.

    This service ensures that trading events are reliably published
    even if the message broker is temporarily unavailable.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create_order_with_event(
        self,
        exchange: str,
        pair: str,
        side: str,
        amount: float,
        price: float,
        order_type: str = "limit",
        strategy: str = "",
    ) -> int:
        """Create a new order and publish an event atomically.

        This method uses the Transactional Outbox Pattern to ensure
        reliable event delivery.

        Args:
            exchange: Exchange name (e.g., "binance")
            pair: Trading pair (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            amount: Order amount
            price: Order price
            order_type: Order type ("limit", "market", etc.)
            strategy: Strategy name

        Returns:
            Trade ID
        """
        async with self._session_factory() as session:
            from app.infrastructure.database.models.trading import (
                FTTrade,
                TransactionalOutbox,
            )
            trade = FTTrade(
                exchange=exchange,
                pair=pair,
                base_currency=pair.split("/")[0] if "/" in pair else pair,
                stake_currency=pair.split("/")[1] if "/" in pair else "USDT",
                open_date=datetime.now(),
                open_rate=price,
                open_rate_requested=price,
                stake_amount=amount * price,
                amount=amount,
                strategy=strategy,
                enter_tag=f"{side}:{order_type}",
                is_open=1,
            )
            session.add(trade)
            await session.flush()

            outbox_event = TransactionalOutbox(
                aggregate_type="trade",
                aggregate_id=str(trade.id),
                event_type="created",
                payload=json.dumps({
                    "trade_id": trade.id,
                    "exchange": exchange,
                    "pair": pair,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "order_type": order_type,
                    "strategy": strategy,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False),
                status="pending",
                created_at=datetime.now(),
            )
            session.add(outbox_event)
            await session.commit()

            logger.info(f"Created trade {trade.id} with outbox event")
            return trade.id

    async def close_order_with_event(
        self,
        trade_id: int,
        close_price: float,
        close_profit: float,
        exit_reason: str = "manual",
    ) -> bool:
        """Close an order and publish an event atomically."""
        async with self._session_factory() as session:
            from app.infrastructure.database.models.trading import (
                FTTrade,
                TransactionalOutbox,
            )
            stmt = select(FTTrade).where(FTTrade.id == trade_id)
            result = await session.execute(stmt)
            trade = result.scalars().first()

            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False

            trade.close_rate = close_price
            trade.close_profit = close_profit
            trade.close_date = datetime.now()
            trade.exit_reason = exit_reason
            trade.is_open = 0

            outbox_event = TransactionalOutbox(
                aggregate_type="trade",
                aggregate_id=str(trade_id),
                event_type="closed",
                payload=json.dumps({
                    "trade_id": trade_id,
                    "close_price": close_price,
                    "close_profit": close_profit,
                    "exit_reason": exit_reason,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False),
                status="pending",
                created_at=datetime.now(),
            )
            session.add(outbox_event)
            await session.commit()

            logger.info(f"Closed trade {trade_id} with outbox event")
            return True

    async def fill_order_with_event(
        self,
        trade_id: int,
        order_id: str,
        filled_amount: float,
        filled_price: float,
    ) -> bool:
        """Record order fill and publish event atomically."""
        async with self._session_factory() as session:
            from app.infrastructure.database.models.trading import (
                FTOrder,
                FTTrade,
                TransactionalOutbox,
            )
            stmt = select(FTTrade).where(FTTrade.id == trade_id)
            result = await session.execute(stmt)
            trade = result.scalars().first()

            if not trade:
                return False

            order = FTOrder(
                ft_trade_id=trade_id,
                order_id=order_id,
                ft_pair=trade.pair,
                ft_order_side="buy" if trade.enter_tag.startswith("buy") else "sell",
                ft_is_open=0,
                ft_amount=filled_amount,
                ft_price=filled_price,
                status="filled",
                order_type="limit",
                side="buy" if trade.enter_tag.startswith("buy") else "sell",
                filled=filled_amount,
                remaining=0,
                cost=filled_amount * filled_price,
                order_filled_date=datetime.now(),
            )
            session.add(order)

            outbox_event = TransactionalOutbox(
                aggregate_type="order",
                aggregate_id=order_id,
                event_type="filled",
                payload=json.dumps({
                    "trade_id": trade_id,
                    "order_id": order_id,
                    "filled_amount": filled_amount,
                    "filled_price": filled_price,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False),
                status="pending",
                created_at=datetime.now(),
            )
            session.add(outbox_event)
            await session.commit()

            return True


__all__ = ["TradingService"]
