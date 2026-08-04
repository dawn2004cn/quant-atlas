from __future__ import annotations

"""Celery: QuestDB/ClickHouse OHLCV ingest retired — prefer Timescale + CSV + Qlib."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_scheduled_questdb_sync() -> dict[str, Any]:
    """Deprecated: QuestDB/ClickHouse 历史入库已下线，统一走 Timescale + CSV + Qlib。"""
    logger.info(
        "questdb/clickhouse OHLCV ingest disabled; use TIMESCALE_TDX_SYNC_BEAT / TDX_DAYK_CELERY_BEAT"
    )
    return {
        "ok": True,
        "skipped": True,
        "reason": "questdb_clickhouse_ingest_retired",
        "preferred": ["timescale", "csv", "qlib"],
    }


from app.celery_app import celery as _celery


def run_full_market_timeseries_backfill(
    *,
    batch_size: int | None = None,
    max_batches: int | None = None,
    offset: int = 0,
    lookback_days: int | None = None,
    truncate_first: bool = False,
    workers: int | None = None,
) -> dict[str, Any]:
    """Deprecated full-market QuestDB/ClickHouse backfill — returns skipped."""
    _ = (batch_size, max_batches, offset, lookback_days, truncate_first, workers)
    return run_scheduled_questdb_sync()


if _celery is not None:

    @_celery.task(name="app.tasks.questdb_sync_tasks.questdb_ohlcv_sync_tick")
    def questdb_ohlcv_sync_tick() -> dict[str, Any]:
        return run_scheduled_questdb_sync()

    @_celery.task(name="app.tasks.questdb_sync_tasks.timeseries_ohlcv_full_backfill")
    def timeseries_ohlcv_full_backfill(
        batch_size: int | None = None,
        max_batches: int | None = None,
        offset: int = 0,
        lookback_days: int | None = None,
        truncate_first: bool = False,
        workers: int | None = None,
    ) -> dict[str, Any]:
        return run_full_market_timeseries_backfill(
            batch_size=batch_size,
            max_batches=max_batches,
            offset=offset,
            lookback_days=lookback_days,
            truncate_first=truncate_first,
            workers=workers,
        )

else:
    questdb_ohlcv_sync_tick = None  # type: ignore[misc, assignment]
    timeseries_ohlcv_full_backfill = None  # type: ignore[misc, assignment]
