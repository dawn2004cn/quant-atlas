from __future__ import annotations
"""SQLAlchemy implementation of TradeRepository."""


from typing import Any
from sqlalchemy import select

from app.domain.ports import TradeRepository
from app.domain.trading_entities import Trade, Order
from app.infrastructure.database.models.trading import FTTrade, FTOrder


class MySQLTradingRepository(TradeRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_trade(self, trade: Trade) -> str:
        session = self._session_factory()
        try:
            if trade.id is None:
                db_trade = FTTrade(
                    exchange=trade.exchange,
                    pair=trade.pair,
                    base_currency=trade.base_currency,
                    stake_currency=trade.stake_currency,
                    is_open=1 if trade.is_open else 0,
                    open_date=trade.open_date,
                    open_rate=trade.open_rate,
                    open_rate_requested=trade.open_rate_requested,
                    stake_amount=trade.stake_amount,
                    amount=trade.amount,
                    stop_loss=trade.stop_loss,
                    stop_loss_pct=trade.stop_loss_pct,
                    initial_stop_loss=trade.initial_stop_loss,
                    initial_stop_loss_pct=trade.initial_stop_loss_pct,
                    is_stop_loss_trailing=1 if trade.is_stop_loss_trailing else 0,
                    leverage=trade.leverage,
                    is_short=1 if trade.is_short else 0,
                    strategy=trade.strategy,
                    enter_tag=trade.enter_tag
                )
                session.add(db_trade)
                session.flush()
                trade.id = db_trade.id
            else:
                db_trade = session.get(FTTrade, trade.id)
                if db_trade:
                    db_trade.is_open = 1 if trade.is_open else 0
                    db_trade.close_date = trade.close_date
                    db_trade.close_rate = trade.close_rate
                    db_trade.close_rate_requested = trade.close_rate_requested
                    db_trade.close_profit = trade.close_profit
                    db_trade.close_profit_abs = trade.close_profit_abs
                    db_trade.stop_loss = trade.stop_loss
                    db_trade.max_rate = trade.max_rate
                    db_trade.min_rate = trade.min_rate
                    db_trade.exit_reason = trade.exit_reason
            session.commit()
            return str(trade.id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_trades(self, symbol: str | None = None, limit: int = 100) -> list[Trade]:
        """List trades (stub implementation)."""
        return []

    def get_open_trades(self) -> list[Trade]:
        session = self._session_factory()
        try:
            stmt = select(FTTrade).where(FTTrade.is_open == 1)
            db_trades = session.scalars(stmt).all()
            return [self._map_db_to_trade(t) for t in db_trades]
        finally:
            session.close()

    def get_trade_by_id(self, trade_id: int) -> Trade | None:
        session = self._session_factory()
        try:
            db_trade = session.get(FTTrade, trade_id)
            if not db_trade:
                return None
            return self._map_db_to_trade(db_trade)
        finally:
            session.close()

    def save_order(self, order: Order) -> int:
        session = self._session_factory()
        try:
            if order.id is None:
                db_order = FTOrder(
                    ft_trade_id=order.ft_trade_id,
                    order_id=order.order_id,
                    ft_pair=order.ft_pair,
                    ft_order_side=order.ft_order_side,
                    ft_is_open=1 if order.ft_is_open else 0,
                )
                session.add(db_order)
                session.flush()
                order.id = db_order.id
            else:
                db_order = session.get(FTOrder, order.id)
                if db_order:
                    db_order.ft_is_open = 1 if order.ft_is_open else 0
                    db_order.ft_fill_date = order.ft_fill_date
                    db_order.ft_fill_rate = order.ft_fill_rate
                    db_order.ft_fee = order.ft_fee
                    db_order.ft_amount = order.ft_amount
                    db_order.ft_remaining = order.ft_remaining
            session.commit()
            return order.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _map_db_to_trade(self, t: FTTrade) -> Trade:
        return Trade(
            id=t.id,
            exchange=t.exchange,
            pair=t.pair,
            base_currency=t.base_currency,
            stake_currency=t.stake_currency,
            is_open=bool(t.is_open),
            open_date=t.open_date,
            open_rate=t.open_rate,
            open_rate_requested=t.open_rate_requested,
            close_date=t.close_date,
            close_rate=t.close_rate,
            close_rate_requested=t.close_rate_requested,
            close_profit=t.close_profit,
            close_profit_abs=t.close_profit_abs,
            stake_amount=t.stake_amount,
            amount=t.amount,
            stop_loss=t.stop_loss,
            stop_loss_pct=t.stop_loss_pct,
            initial_stop_loss=t.initial_stop_loss,
            initial_stop_loss_pct=t.initial_stop_loss_pct,
            is_stop_loss_trailing=bool(t.is_stop_loss_trailing),
            max_rate=t.max_rate,
            min_rate=t.min_rate,
            exit_reason=t.exit_reason,
            strategy=t.strategy,
            enter_tag=t.enter_tag,
            leverage=t.leverage,
            is_short=bool(t.is_short),
        )
