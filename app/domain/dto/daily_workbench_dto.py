from __future__ import annotations

from typing import Any, TypedDict


class WorkbenchDecisionEvidenceDTO(TypedDict):
    kind: str
    label: str
    value: str
    confidence: float


class WorkbenchDecisionDTO(TypedDict, total=False):
    stance: str
    score: int
    action: str
    reasons: list[str]
    confidence: float
    evidence: list[WorkbenchDecisionEvidenceDTO]


class WorkbenchFocusContextDTO(TypedDict, total=False):
    symbol: str | None
    market: str
    symbol_label: str | None


class WorkbenchHealthBannerDTO(TypedDict, total=False):
    level: str
    message: str
    headline: str
    summary: str
    allow_live_trading: bool
    critical_count: int
    warning_count: int
    stale_data: bool
    quotes_full_dump_count: int
    quotes_full_dump_warn: bool
    quotes_full_dump_threshold: int


class WorkbenchMorningCallSlideDTO(TypedDict):
    id: str
    title: str
    level: str
    items: list[str]


class WorkbenchMorningCallDTO(TypedDict, total=False):
    slides: list[WorkbenchMorningCallSlideDTO]
    active_index: int


class WorkbenchWatchlistHealthDTO(TypedDict):
    items: list[dict[str, Any]]
    summary: str


class WorkbenchSignalFlagPreviewDTO(TypedDict, total=False):
    pool_date: str
    count: int
    items: list[dict[str, Any]]
    message: str


class WorkbenchTaskDigestDTO(TypedDict, total=False):
    backend: str
    recent_total: int
    fail_or_warn: int
    last_items: list[dict[str, Any]]


class WorkbenchTimeseriesBeatDigestDTO(TypedDict, total=False):
    available: bool
    enabled: bool
    schedule_label: str
    last_run_at: str
    last_ok: bool
    sync_in_progress: bool
    history_count: int
    error: str


class WorkbenchIntegrationDigestDTO(TypedDict, total=False):
    available: bool
    summary: str
    mysql_enabled: bool
    issues: list[str]
    issue_count: int
    timeseries_beat: WorkbenchTimeseriesBeatDigestDTO


class WorkbenchReviewStripDTO(TypedDict, total=False):
    daily: Any
    weekly: Any


class WorkbenchTradePlanStripDTO(TypedDict, total=False):
    symbol: str | None
    name: str | None
    entry_price: float | None
    stop_loss: float | None
    take_profit_1: float | None
    risk_reward_ratio: float | None
    error: str


class WorkbenchHeadlineDTO(TypedDict, total=False):
    title: str
    source: str
    published_at: str
    url: str
    summary: str
    signal_tag: str
    sentiment_score: float
    affected_symbols: list[str]
    confidence: float


class DailyWorkbenchSnapshotDTO(TypedDict, total=False):
    generated_at: str
    market: str
    focus_context: WorkbenchFocusContextDTO
    health_banner: WorkbenchHealthBannerDTO
    morning_call: WorkbenchMorningCallDTO
    decision: WorkbenchDecisionDTO
    market_panorama: dict[str, Any]
    market_sentiment: dict[str, Any]
    macro_indices: list[dict[str, Any]]
    watchlist_health: WorkbenchWatchlistHealthDTO
    limit_up_stocks: list[dict[str, Any]]
    limit_up_stats: dict[str, int]
    dragon_list: dict[str, Any]
    observation_cards: list[dict[str, Any]]
    signal_flag_preview: WorkbenchSignalFlagPreviewDTO
    task_digest: WorkbenchTaskDigestDTO
    integration_digest: WorkbenchIntegrationDigestDTO
    recommendations_preview: dict[str, Any]
    review_strip: WorkbenchReviewStripDTO
    headlines: list[WorkbenchHeadlineDTO]
    trade_plan_strip: WorkbenchTradePlanStripDTO
    fingpt_available: bool
    data_mode: str
    demo_parts: list[str]
