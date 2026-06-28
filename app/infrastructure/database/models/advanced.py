from __future__ import annotations

"""ORM models for AI Research, Foundation Models, and Data Caching."""


from datetime import date, datetime

from sqlalchemy import Date, DateTime, Double, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..orm import Base


class YanbaoItem(Base):
    __tablename__ = "yanbao_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    stock_code: Mapped[str | None] = mapped_column(String(16), index=True)
    org_name: Mapped[str | None] = mapped_column(String(128))
    pub_date: Mapped[str | None] = mapped_column(String(32))
    report_url: Mapped[str | None] = mapped_column(String(1024))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    crawl_batch: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class ArchivedNews(Base):
    __tablename__ = "archived_news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("market", "symbol", "scope", "content_hash", name="ux_arch_news"),
        # P0: Prefix scan for latest_fetched_at + list_for_symbol
        Index("idx_news_market_symbol", "market", "symbol"),
        # P0: Dedup upsert query
        Index("idx_news_lookup", "market", "symbol", "scope", "content_hash"),
    )


class SignalFlagPool(Base):
    __tablename__ = "signal_flag_pool"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[float] = mapped_column(Double, default=0.0)
    change_pct: Mapped[float] = mapped_column(Double, default=0.0)
    volume: Mapped[float] = mapped_column(Double, default=0.0)
    amount: Mapped[float] = mapped_column(Double, default=0.0)
    turnover: Mapped[float] = mapped_column(Double, default=0.0)
    source: Mapped[str | None] = mapped_column(String(64))
    industry: Mapped[str | None] = mapped_column(String(128))
    pe: Mapped[float] = mapped_column(Double, default=0.0)
    pb: Mapped[float] = mapped_column(Double, default=0.0)
    signal_strategies: Mapped[str] = mapped_column(Text, nullable=False)
    signal_strategies_sell: Mapped[str | None] = mapped_column(Text)
    long_horizon: Mapped[str] = mapped_column(Text, nullable=False)
    mid_horizon: Mapped[str] = mapped_column(Text, nullable=False)
    short_horizon: Mapped[str] = mapped_column(Text, nullable=False)
    safety_score: Mapped[float] = mapped_column(Double, default=0.0)
    extra_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("pool_date", "code", name="ux_sfp"),
        # P2: ORDER BY amount DESC by pool_date (get_pool)
        Index("idx_sfp_date_amount", "pool_date", "amount"),
    )


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dashboard: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_price: Mapped[float] = mapped_column(Double, default=0.0)
    prediction_type: Mapped[str | None] = mapped_column(String(64))
    validation_status: Mapped[str | None] = mapped_column(String(32), default="pending", index=True)
    validation_score: Mapped[float] = mapped_column(Double, default=0.0)


class FinGPTPrediction(Base):
    __tablename__ = "fingpt_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    source_ref: Mapped[str | None] = mapped_column(String(128))
    predicted_movement: Mapped[str | None] = mapped_column(String(64))
    positive_factors: Mapped[str | None] = mapped_column(Text)
    potential_concerns: Mapped[str | None] = mapped_column(Text)
    analysis_summary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Double, default=0.0)
    actual_movement: Mapped[float] = mapped_column(Double, default=0.0)
    is_correct: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        UniqueConstraint("ticker", "prediction_date", name="ux_fingpt_ticker_date"),
    )


class FinGPTSentiment(Base):
    __tablename__ = "fingpt_sentiment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    news_id: Mapped[str | None] = mapped_column(String(128))
    summary_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    source_ref: Mapped[str | None] = mapped_column(String(128))
    sentiment_score: Mapped[float] = mapped_column(Double, default=0.0)
    key_entities: Mapped[str | None] = mapped_column(String(255))
    impact_level: Mapped[str | None] = mapped_column(String(32))
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        UniqueConstraint("ticker", "summary_hash", name="ux_fingpt_sent_ticker_hash"),
    )


class KronosModel(Base):
    __tablename__ = "kronos_models"
    model_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    hf_path: Mapped[str | None] = mapped_column(String(255))
    local_path: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class KronosPrediction(Base):
    __tablename__ = "kronos_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("kronos_models.model_id"), nullable=False, index=True)
    prediction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_json: Mapped[str] = mapped_column(Text, nullable=False)
    actual_json: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class OpenBBProviderConfig(Base):
    __tablename__ = "openbb_provider_configs"
    provider_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(String(512))
    is_enabled: Mapped[int] = mapped_column(SmallInteger, default=1)
    settings_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class OpenBBDataCache(Base):
    __tablename__ = "openbb_data_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timeframe: Mapped[str | None] = mapped_column(String(16), index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class QuantMLFactor(Base):
    __tablename__ = "quantml_factors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    ic_mean: Mapped[float | None] = mapped_column(Double)
    icir: Mapped[float | None] = mapped_column(Double)
    long_average: Mapped[float | None] = mapped_column(Double)
    long_short: Mapped[float | None] = mapped_column(Double)
    t_stat: Mapped[float | None] = mapped_column(Double)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class AgentMarketInsight(Base):
    __tablename__ = "agent_market_insights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    sentiment_label: Mapped[str | None] = mapped_column(String(32))
    trend_prediction: Mapped[str | None] = mapped_column(String(64))
    hot_sectors: Mapped[str | None] = mapped_column(Text)
    full_analysis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class AgentReportInterpretation(Base):
    __tablename__ = "agent_report_interpretations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(128))
    report_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    key_takeaways: Mapped[str | None] = mapped_column(Text)
    market_impact: Mapped[str | None] = mapped_column(String(64))
    full_interpretation: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class NewsSymbolMeta(Base):
    __tablename__ = "news_symbol_meta"
    market: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_name: Mapped[str | None] = mapped_column(String(256))
    industry_hint: Mapped[str | None] = mapped_column(String(256))
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class AICommitteeSelectionRun(Base):
    __tablename__ = "ai_committee_selection_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    capital: Mapped[float] = mapped_column(Double, default=500000.0)
    market_regime: Mapped[str] = mapped_column(String(32), default="sideways", index=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    selected_count: Mapped[int] = mapped_column(Integer, default=0)
    agents_json: Mapped[str] = mapped_column(Text, nullable=False)
    indexes_json: Mapped[str] = mapped_column(Text, nullable=False)
    strategies_json: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class AICommitteeSelectionTrade(Base):
    __tablename__ = "ai_committee_selection_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(16), default="BUY")
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    entry_price: Mapped[float] = mapped_column(Double, default=0.0)
    current_price: Mapped[float] = mapped_column(Double, default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    capital_used: Mapped[float] = mapped_column(Double, default=0.0)
    stop_loss: Mapped[float] = mapped_column(Double, default=0.0)
    take_profit: Mapped[float] = mapped_column(Double, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Double, default=0.0)
    sniper_score: Mapped[float] = mapped_column(Double, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
