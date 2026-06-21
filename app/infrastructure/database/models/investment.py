from __future__ import annotations
"""ORM models for Investment Managers, Portfolios, and User Race."""


from typing import Optional
from sqlalchemy import Index, String, Integer, Double, ForeignKey, Text, SmallInteger, BIGINT, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class InvestmentManager(Base):
    __tablename__ = "investment_managers"

    manager_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    cohort: Mapped[str] = mapped_column(String(16), nullable=False)
    deployed_at: Mapped[Optional[str]] = mapped_column(String(32))
    active: Mapped[int] = mapped_column(SmallInteger, default=0, index=True)
    tagline: Mapped[str] = mapped_column(String(512), default="")
    specialty: Mapped[str] = mapped_column(String(512), default="")


class ManagerNAV(Base):
    __tablename__ = "manager_nav"

    manager_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nav_date: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    equity: Mapped[float] = mapped_column(Double, nullable=False)
    cash: Mapped[float] = mapped_column(Double, nullable=False)
    total_fee: Mapped[float] = mapped_column(Double, default=0.0)
    total_tax: Mapped[float] = mapped_column(Double, default=0.0)
    note: Mapped[str] = mapped_column(String(255), default="")

    __table_args__ = (
        PrimaryKeyConstraint("manager_id", "nav_date"),
    )


class ManagerTrade(Base):
    __tablename__ = "manager_trades"

    trade_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    manager_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float] = mapped_column(Double, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    fee: Mapped[float] = mapped_column(Double, default=0.0)
    tax: Mapped[float] = mapped_column(Double, default=0.0)

    __table_args__ = (
        # P1: Ordered listing per manager
        Index("idx_manager_trades_mdate", "manager_id", "trade_date"),
    )


class ManagerHoldingsSnap(Base):
    __tablename__ = "manager_holdings_snap"

    manager_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    snap_date: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Double, nullable=False)
    market_price: Mapped[float] = mapped_column(Double, nullable=False)
    market_value: Mapped[float] = mapped_column(Double, nullable=False)
    weight: Mapped[float] = mapped_column(Double, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("manager_id", "snap_date", "symbol"),
    )


class ManagerPositionState(Base):
    __tablename__ = "manager_positions_state"

    manager_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Double, nullable=False)
    entry_cost: Mapped[float] = mapped_column(Double, nullable=False)
    high_px: Mapped[float] = mapped_column(Double, nullable=False)
    entry_date: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("manager_id", "symbol"),
    )


class UserRaceAccount(Base):
    __tablename__ = "user_race_account"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cash: Mapped[float] = mapped_column(Double, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class UserRaceTrade(Base):
    __tablename__ = "user_race_trades"

    trade_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    price: Mapped[float] = mapped_column(Double, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    fee: Mapped[float] = mapped_column(Double, default=0.0)
    tax: Mapped[float] = mapped_column(Double, default=0.0)
    note: Mapped[str] = mapped_column(String(255), default="")

    __table_args__ = (
        # P2: Ordered listing per account
        Index("idx_user_race_trades_adate", "account_id", "trade_date"),
    )


class UserRaceNAV(Base):
    __tablename__ = "user_race_nav"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nav_date: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    equity: Mapped[float] = mapped_column(Double, nullable=False)
    cash: Mapped[float] = mapped_column(Double, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("account_id", "nav_date"),
    )
