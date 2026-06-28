from __future__ import annotations

"""ORM models for Market data, Stocks, and Watchlists."""


from datetime import datetime

from sqlalchemy import JSON, DateTime, Double, ForeignKey, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'user_id'),
    )


class StockGroup(Base):
    __tablename__ = "stock_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="")
    is_default: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_stock_group_user_name'),
    )

    items: Mapped[list[StockGroupItem]] = relationship(
        "StockGroupItem", back_populates="group", cascade="all, delete-orphan", lazy="selectin"
    )


class StockGroupItem(Base):
    __tablename__ = "stock_group_items"
    group_id: Mapped[int] = mapped_column(ForeignKey("stock_groups.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    is_removed: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[StockGroup] = relationship("StockGroup", back_populates="items")


class Stock(Base):
    __tablename__ = "stocks"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    price: Mapped[float] = mapped_column(Double, default=0.0)
    change_pct: Mapped[float] = mapped_column(Double, default=0.0)
    change_amount: Mapped[float] = mapped_column(Double, default=0.0)
    prev_close: Mapped[float] = mapped_column(Double, default=0.0)
    volume: Mapped[float] = mapped_column(Double, default=0.0)
    amount: Mapped[float] = mapped_column(Double, default=0.0, index=True)
    turnover: Mapped[float] = mapped_column(Double, default=0.0)
    volume_ratio: Mapped[float] = mapped_column(Double, default=0.0)
    amplitude: Mapped[float] = mapped_column(Double, default=0.0)
    pe: Mapped[float] = mapped_column(Double, default=0.0)
    pb: Mapped[float] = mapped_column(Double, default=0.0)
    total_market_cap: Mapped[float] = mapped_column(Double, default=0.0)
    industry: Mapped[str] = mapped_column(String(128), default="")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class StockHistory(Base):
    __tablename__ = "stock_history"
    stock_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    date: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    open: Mapped[float] = mapped_column(Double, default=0.0)
    high: Mapped[float] = mapped_column(Double, default=0.0)
    low: Mapped[float] = mapped_column(Double, default=0.0)
    close: Mapped[float] = mapped_column(Double, default=0.0)
    volume: Mapped[float] = mapped_column(Double, default=0.0)
    amount: Mapped[float] = mapped_column(Double, default=0.0)

    __table_args__ = (
        PrimaryKeyConstraint("stock_code", "date"),
    )


class CNStockBasic(Base):
    __tablename__ = "cn_stock_basics"
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    listing_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    delist_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_st: Mapped[bool] = mapped_column(default=False)
    listing_status: Mapped[str] = mapped_column(String(16), default="L")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)


class TDXBlock(Base):
    __tablename__ = "tdx_blocks"
    block_kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    block_name: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("block_kind", "block_name"),
    )


class TDXBlockItem(Base):
    __tablename__ = "tdx_block_items"
    block_kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    block_name: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("block_kind", "block_name", "symbol"),
    )


class CNFinanceSnapshot(Base):
    __tablename__ = "cn_finance_snapshots"
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    report_date: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    total_shares: Mapped[float] = mapped_column(Double, default=0.0)
    float_shares: Mapped[float] = mapped_column(Double, default=0.0)
    eps: Mapped[float] = mapped_column(Double, default=0.0)
    bps: Mapped[float] = mapped_column(Double, default=0.0)
    net_profit: Mapped[float] = mapped_column(Double, default=0.0)
    revenue: Mapped[float] = mapped_column(Double, default=0.0)
    fetched_at: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_json: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        PrimaryKeyConstraint("symbol", "report_date"),
    )


class TDXWatchlist(Base):
    __tablename__ = "tdx_watchlists"
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    items: Mapped[list[TDXWatchlistItem]] = relationship(
        "TDXWatchlistItem", back_populates="watchlist", cascade="all, delete-orphan", lazy="selectin"
    )


class TDXWatchlistItem(Base):
    __tablename__ = "tdx_watchlist_items"
    watchlist_name: Mapped[str] = mapped_column(ForeignKey("tdx_watchlists.name"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    watchlist: Mapped[TDXWatchlist] = relationship("TDXWatchlist", back_populates="items")


class MarketSentiment(Base):
    __tablename__ = "market_sentiment"
    market: Mapped[str] = mapped_column(String(16), primary_key=True)
    up_count: Mapped[int] = mapped_column(Integer, default=0)
    down_count: Mapped[int] = mapped_column(Integer, default=0)
    flat_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class MarketSentimentDaily(Base):
    __tablename__ = "market_sentiment_daily"
    market: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    up_count: Mapped[int] = mapped_column(Integer, default=0)
    down_count: Mapped[int] = mapped_column(Integer, default=0)
    flat_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        PrimaryKeyConstraint("market", "trade_date"),
    )


class LonghuDaily(Base):
    __tablename__ = "longhu_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(512))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("trade_date", "code", name="ux_longhu"),
    )


class BasicDataMeta(Base):
    __tablename__ = "basic_data_meta"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class CNFinancialStash(Base):
    __tablename__ = "cn_financial_stash"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class TdxGpcwFinancial(Base):
    __tablename__ = "tdx_gpcw_financial"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    indexed_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    report_date: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    non_zero_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        UniqueConstraint("code", "report_date", name="uix_code_report_date"),
    )


class TdxGpcwAudit(Base):
    __tablename__ = "tdx_gpcw_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_file: Mapped[str] = mapped_column(String(32), nullable=False)
    report_date: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stocks_processed: Mapped[int] = mapped_column(Integer, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    finished_at: Mapped[str] = mapped_column(String(64), nullable=True)
    duration_sec: Mapped[float] = mapped_column(Double, nullable=True)


class EMHotSectorSnapshot(Base):
    """热点板块入库批次（东财概念/行业涨幅榜）。"""

    __tablename__ = "em_hot_sector_snapshots"
    snapshot_at: Mapped[str] = mapped_column(String(32), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ingest_kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sector_count: Mapped[int] = mapped_column(Integer, default=0)
    member_rows: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="eastmoney")


class EMHotSector(Base):
    __tablename__ = "em_hot_sectors"
    snapshot_at: Mapped[str] = mapped_column(String(32), primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    change_pct: Mapped[float] = mapped_column(Double, default=0.0)
    price: Mapped[float] = mapped_column(Double, default=0.0)
    amount: Mapped[float] = mapped_column(Double, default=0.0)
    volume: Mapped[float] = mapped_column(Double, default=0.0)
    turnover_rate: Mapped[float] = mapped_column(Double, default=0.0)
    rank_no: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_at", "sector_code"),
    )


class EMHotSectorMember(Base):
    __tablename__ = "em_hot_sector_members"
    snapshot_at: Mapped[str] = mapped_column(String(32), primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    change_pct: Mapped[float] = mapped_column(Double, default=0.0)
    price: Mapped[float] = mapped_column(Double, default=0.0)
    amount: Mapped[float] = mapped_column(Double, default=0.0)
    volume: Mapped[float] = mapped_column(Double, default=0.0)

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_at", "sector_code", "symbol"),
    )
