from __future__ import annotations
"""ORM models for Freqtrade-style Trading and Hyperswitch-style Payments."""


from datetime import datetime
from sqlalchemy import String, Integer, Double, DateTime, ForeignKey, Text, SmallInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class FTTrade(Base):
    __tablename__ = "ft_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    pair: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_currency: Mapped[str | None] = mapped_column(String(16))
    stake_currency: Mapped[str | None] = mapped_column(String(16))
    is_open: Mapped[int] = mapped_column(SmallInteger, default=1, index=True)
    open_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open_rate: Mapped[float] = mapped_column(Double, nullable=False)
    open_rate_requested: Mapped[float | None] = mapped_column(Double)
    close_date: Mapped[datetime | None] = mapped_column(DateTime)
    close_rate: Mapped[float | None] = mapped_column(Double)
    close_rate_requested: Mapped[float | None] = mapped_column(Double)
    close_profit: Mapped[float | None] = mapped_column(Double)
    close_profit_abs: Mapped[float | None] = mapped_column(Double)
    stake_amount: Mapped[float] = mapped_column(Double, nullable=False)
    amount: Mapped[float] = mapped_column(Double, nullable=False)
    stop_loss: Mapped[float | None] = mapped_column(Double)
    stop_loss_pct: Mapped[float | None] = mapped_column(Double)
    initial_stop_loss: Mapped[float | None] = mapped_column(Double)
    initial_stop_loss_pct: Mapped[float | None] = mapped_column(Double)
    is_stop_loss_trailing: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    max_rate: Mapped[float | None] = mapped_column(Double)
    min_rate: Mapped[float | None] = mapped_column(Double)
    exit_reason: Mapped[str | None] = mapped_column(String(64))
    strategy: Mapped[str | None] = mapped_column(String(64))
    enter_tag: Mapped[str | None] = mapped_column(String(64))
    leverage: Mapped[float | None] = mapped_column(Double, default=1.0)
    is_short: Mapped[int | None] = mapped_column(SmallInteger, default=0)

    __table_args__ = (
        # P1: Filter by exchange + is_open (list_open_trades_by_exchange)
        Index("idx_trades_exchange_open", "exchange", "is_open"),
    )

    orders: Mapped[list[FTOrder]] = relationship(
        "FTOrder", back_populates="trade", cascade="all, delete-orphan", lazy="selectin"
    )


class FTOrder(Base):
    __tablename__ = "ft_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ft_trade_id: Mapped[int] = mapped_column(ForeignKey("ft_trades.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ft_pair: Mapped[str] = mapped_column(String(32), nullable=False)
    ft_order_side: Mapped[str] = mapped_column(String(32), nullable=False)
    ft_is_open: Mapped[int] = mapped_column(SmallInteger, default=1)
    ft_amount: Mapped[float] = mapped_column(Double, nullable=False)
    ft_price: Mapped[float] = mapped_column(Double, nullable=False)
    status: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(32))
    order_type: Mapped[str | None] = mapped_column(String(64))
    side: Mapped[str | None] = mapped_column(String(32))
    filled: Mapped[float | None] = mapped_column(Double, default=0.0)
    remaining: Mapped[float | None] = mapped_column(Double)
    cost: Mapped[float | None] = mapped_column(Double)
    order_date: Mapped[datetime | None] = mapped_column(DateTime)
    order_filled_date: Mapped[datetime | None] = mapped_column(DateTime)

    trade: Mapped[FTTrade] = relationship("FTTrade", back_populates="orders")


class GatewayConfig(Base):
    __tablename__ = "gateway_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gateway_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    config_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    amount: Mapped[float] = mapped_column(Double, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    gateway_id: Mapped[int | None] = mapped_column(ForeignKey("gateway_configs.id"))
    external_id: Mapped[str | None] = mapped_column(String(255))
    customer_id: Mapped[str | None] = mapped_column(String(128), index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class PaymentRefund(Base):
    __tablename__ = "payment_refunds"

    refund_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(ForeignKey("payment_intents.intent_id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Double, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    external_refund_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class TransactionalOutbox(Base):
    """Transactional Outbox for reliable event publishing.

    This table implements the Transactional Outbox Pattern to ensure
    reliable event delivery. Instead of directly publishing events,
    we write them to this table within the same transaction as the
    business operation. A separate process then reads from this
    table and publishes events to message brokers.

    Usage:
        1. Within a DB transaction, write your business data + an outbox record
        2. Commit the transaction (atomicity guaranteed)
        3. Outbox processor reads unprocessed records and publishes them
        4. After successful publish, mark record as processed
    """
    __tablename__ = "transactional_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # P0: Outbox processor fetches pending events ordered by time
        Index("idx_outbox_status_created", "status", "created_at"),
        # P0: Aggregate-type queries (lookup events by entity)
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id", "status"),
        # P0: Cleanup old processed events
        Index("idx_outbox_cleanup", "status", "processed_at"),
    )
