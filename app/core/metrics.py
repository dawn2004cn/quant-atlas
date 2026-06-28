"""Prometheus metrics definition for quant-atlas.

Provides both domain-specific metrics (Rust indicator, sync service) and
cross-cutting observability metrics (request duration, error count, cache, etc.).

All dependencies on prometheus_client are optional — graceful degradation when
the library is not installed.
"""
from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    Counter = Histogram = Gauge = None  # type: ignore[misc, assignment]

# ---------------------------------------------------------------------------
# Domain-specific: Rust indicator calculation
# ---------------------------------------------------------------------------

RUST_INDICATOR_LATENCY = (
    Histogram(
        "quant_rust_indicator_latency_seconds",
        "Time spent in Rust indicator calculation",
        ["indicator_type"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

INDICATOR_ERRORS = (
    Counter(
        "quant_indicator_calculation_errors_total",
        "Total number of errors during indicator calculation",
        ["provider"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Domain-specific: Sync service
# ---------------------------------------------------------------------------

SYNC_ROWS_PROCESSED = (
    Counter(
        "quant_sync_rows_processed_total",
        "Total rows synced to MySQL",
        ["market"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

SYNC_LATENCY = (
    Histogram(
        "quant_sync_latency_seconds",
        "Latency of synchronization per stock",
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: Request observability
# ---------------------------------------------------------------------------

REQUEST_DURATION = (
    Histogram(
        "app_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint", "status"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

REQUEST_COUNT = (
    Counter(
        "app_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

ERROR_COUNT = (
    Counter(
        "app_errors_total",
        "Total errors by type",
        ["error_type", "endpoint"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: Task queue (Celery)
# ---------------------------------------------------------------------------

TASK_DURATION = (
    Histogram(
        "celery_task_duration_seconds",
        "Celery task execution duration in seconds",
        ["task_name"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: Database
# ---------------------------------------------------------------------------

DB_QUERY_DURATION = (
    Histogram(
        "db_query_duration_seconds",
        "Database query execution time in seconds",
        ["query_type", "table"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: Cache
# ---------------------------------------------------------------------------

CACHE_HITS = (
    Counter(
        "cache_hits_total",
        "Total cache hits",
        ["cache_name"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

CACHE_MISSES = (
    Counter(
        "cache_misses_total",
        "Total cache misses",
        ["cache_name"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: AI / LLM calls
# ---------------------------------------------------------------------------

AI_CALL_DURATION = (
    Histogram(
        "ai_call_duration_seconds",
        "Duration of AI/LLM API calls in seconds",
        ["model", "call_type"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

AI_CALLS_TOTAL = (
    Counter(
        "app_ai_calls_total",
        "Total AI/LLM API calls",
        ["model", "call_type"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

BACKTEST_COMPLETED = (
    Counter(
        "app_backtest_completed_total",
        "Completed backtest runs",
        ["engine", "outcome"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

# ---------------------------------------------------------------------------
# Cross-cutting: Application facades
# ---------------------------------------------------------------------------

FACADE_CALL_DURATION = (
    Histogram(
        "app_facade_call_duration_seconds",
        "Facade method call duration in seconds",
        ["facade", "method"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)

FACADE_ERRORS = (
    Counter(
        "app_facade_errors_total",
        "Total facade method errors",
        ["facade", "method", "error_type"],
    )
    if HAS_PROMETHEUS
    else None  # type: ignore[assignment]
)
