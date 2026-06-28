from __future__ import annotations
"""ORM models for Execution Feedback and Slippage Analysis.

Phase 42: 交易反馈环与滑点分析

This module provides data models for:
- Tracking order submission vs fill times (latency)
- Recording expected price vs actual fill price (slippage)
- Storing execution quality metrics
- Feeding back to backtest engine for parameter adjustment
"""


from datetime import datetime
from sqlalchemy import String, Integer, Double, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..orm import Base


class ExecutionRecord(Base):
    """Record of a single trade execution with slippage data."""

    __tablename__ = "execution_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Order info
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy/sell

    # Price info
    expected_price: Mapped[float] = mapped_column(Double, nullable=False)
    fill_price: Mapped[float] = mapped_column(Double, nullable=False)
    slippage: Mapped[float] = mapped_column(Double, nullable=False)  # fill_price - expected_price
    slippage_pct: Mapped[float] = mapped_column(Double, nullable=False)  # slippage / expected_price * 100

    # Volume info
    expected_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_rate: Mapped[float] = mapped_column(Double, nullable=False)  # fill_volume / expected_volume

    # Timing info
    order_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    fill_time: Mapped[datetime | None] = mapped_column(DateTime)
    latency_ms: Mapped[float | None] = mapped_column(Double)  # fill_time - order_time in ms

    # Market context
    market_price_at_order: Mapped[float | None] = mapped_column(Double)
    spread_at_order: Mapped[float | None] = mapped_column(Double)
    volatility_at_order: Mapped[float | None] = mapped_column(Double)

    # Execution quality
    execution_quality: Mapped[str] = mapped_column(String(32), default="normal")  # normal/poor/excellent
    reason_code: Mapped[str | None] = mapped_column(String(64))  # partial_fill/timeout/cancelled/etc

    # Metadata
    gateway: Mapped[str] = mapped_column(String(64), default="qmt")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_exec_symbol_date", "symbol", "order_time"),
        Index("idx_exec_strategy", "strategy_id"),
        # P1: Strategy + time range queries (execution feedback)
        Index("idx_exec_strategy_time", "strategy_id", "order_time"),
    )


class SlippageStatistics(Base):
    """Aggregated slippage statistics by strategy/symbol/time period."""

    __tablename__ = "slippage_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Grouping
    strategy_id: Mapped[str | None] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM-DD or YYYY-MM

    # Statistics
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    filled_orders: Mapped[int] = mapped_column(Integer, default=0)
    fill_rate: Mapped[float] = mapped_column(Double, default=0.0)

    avg_slippage: Mapped[float] = mapped_column(Double, default=0.0)
    avg_slippage_pct: Mapped[float] = mapped_column(Double, default=0.0)
    max_slippage: Mapped[float] = mapped_column(Double, default=0.0)
    min_slippage: Mapped[float] = mapped_column(Double, default=0.0)
    std_slippage: Mapped[float] = mapped_column(Double, default=0.0)

    avg_latency_ms: Mapped[float] = mapped_column(Double, default=0.0)
    max_latency_ms: Mapped[float] = mapped_column(Double, default=0.0)

    # Cost impact
    total_slippage_cost: Mapped[float] = mapped_column(Double, default=0.0)
    avg_cost_per_order: Mapped[float] = mapped_column(Double, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("strategy_id", "symbol", "period", name="uq_slippage_stats"),
        Index("idx_slippage_symbol", "symbol"),
    )


class BacktestAdjustment(Base):
    """Backtest parameter adjustments based on real execution data."""

    __tablename__ = "backtest_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Original params
    original_slippage_model: Mapped[str] = mapped_column(String(64), default="fixed")
    original_slippage_value: Mapped[float] = mapped_column(Double, default=0.0)

    # Adjusted params based on real data
    adjusted_slippage_model: Mapped[str] = mapped_column(String(64), default="dynamic")
    adjusted_slippage_value: Mapped[float] = mapped_column(Double, default=0.0)
    adjustment_reason: Mapped[str] = mapped_column(Text)

    # Impact analysis
    original_backtest_return: Mapped[float | None] = mapped_column(Double)
    adjusted_backtest_return: Mapped[float | None] = mapped_column(Double)
    return_difference: Mapped[float | None] = mapped_column(Double)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    applied: Mapped[int] = mapped_column(Integer, default=0)  # 0=pending, 1=applied

    __table_args__ = (
        Index("idx_adj_strategy", "strategy_id"),
    )


__all__ = [
    "ExecutionRecord",
    "SlippageStatistics",
    "BacktestAdjustment",
]
