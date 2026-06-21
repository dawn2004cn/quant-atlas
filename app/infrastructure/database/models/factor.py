from __future__ import annotations
"""ORM models for Factor Management and Metadata.

This module provides the data model for storing factor information
and their performance metadata, enabling factor "survival of the fittest".

Factor Metadata includes:
- Basic info: name, expression, category
- Performance: IC_Mean, IC_Std, IR, Decay Rate
- Lifecycle: effective date, expiration date, status
- Governance: version, owner, tags
"""


from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Double, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..orm import Base


class FactorMetadata(Base):
    """Factor metadata - stores factor governance information."""

    __tablename__ = "factor_metadata"

    factor_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    factor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    factor_expression: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    ic_mean: Mapped[float] = mapped_column(Double, default=0.0, index=True)
    ic_std: Mapped[float] = mapped_column(Double, default=0.0)
    ir: Mapped[float] = mapped_column(Double, default=0.0, index=True)
    ic_t_stat: Mapped[float] = mapped_column(Double, default=0.0)
    win_rate: Mapped[float] = mapped_column(Double, default=0.0)

    decay_rate: Mapped[float] = mapped_column(Double, default=0.0)
    half_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    turnover_rate: Mapped[float] = mapped_column(Double, default=0.0)

    effective_date: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    expiration_date: Mapped[Optional[str]] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    version: Mapped[int] = mapped_column(Integer, default=1)
    owner: Mapped[str] = mapped_column(String(64), default="system")
    tags: Mapped[Optional[str]] = mapped_column(Text)

    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("factor_name", "version", name="uq_factor_name_version"),
        Index("idx_factor_perf", "ic_mean", "ir", "status"),
    )


class FactorICRecord(Base):
    """Factor IC (Information Coefficient) time series.

    Stores daily IC values for tracking factor performance over time.
    """

    __tablename__ = "factor_ic_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    calc_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    ic_value: Mapped[float] = mapped_column(Double, nullable=False)
    rank_ic_value: Mapped[Optional[float]] = mapped_column(Double)

    forward_return: Mapped[float] = mapped_column(Double, default=0.0)
    universe: Mapped[str] = mapped_column(String(64), default="all")

    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("factor_id", "calc_date", "universe", name="uq_factor_ic_date"),
        Index("idx_ic_date", "calc_date"),
        # P0: Factor charting query (factor_id + date range)
        Index("idx_ic_factor_date", "factor_id", "calc_date"),
    )


class FactorExposure(Base):
    """Factor exposure values for each symbol on each date."""

    __tablename__ = "factor_exposure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    calc_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    exposure_value: Mapped[float] = mapped_column(Double, nullable=False)
    is_valid: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("factor_id", "symbol", "calc_date", name="uq_factor_exposure"),
        Index("idx_exposure_date", "calc_date", "factor_id"),
    )


class FactorDecayLog(Base):
    """Factor decay detection and logging."""

    __tablename__ = "factor_decay_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    detection_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    ic_mean_current: Mapped[float] = mapped_column(Double, default=0.0)
    ic_mean_historical: Mapped[float] = mapped_column(Double, default=0.0)
    decay_ratio: Mapped[float] = mapped_column(Double, default=0.0)

    severity: Mapped[str] = mapped_column(String(32), default="normal")
    action_taken: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_decay_factor_date", "factor_id", "detection_date"),
    )


class FactorCatalog(Base):
    """Factor catalog for organizing and discovering factors."""

    __tablename__ = "factor_catalog"

    catalog_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    catalog_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)

    factor_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("catalog_name", "parent_id", name="uq_catalog_name_parent"),
    )


__all__ = [
    "FactorMetadata",
    "FactorICRecord",
    "FactorExposure",
    "FactorDecayLog",
    "FactorCatalog",
]