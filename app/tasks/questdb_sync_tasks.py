from __future__ import annotations

"""Celery: sync TDX lday daily bars into QuestDB + ClickHouse."""

from typing import Any

from app.core.logger import get_logger
from app.modules.data.services.timeseries_ohlcv_sync_service import (
    run_timeseries_ohlcv_backfill,
    run_timeseries_ohlcv_sync,
)

logger = get_logger(__name__)


def run_scheduled_questdb_sync() -> dict[str, Any]:
    """Beat：全市场增量（按各库 max(trade_date) 补 TDX 新 bar）。"""
    from app.core.runtime_config import get_runtime_int

    result = run_timeseries_ohlcv_sync(
        mode="incremental",
        all_market=True,
        limit=get_runtime_int("TIMESERIES_SYNC_LIMIT", 0),
        max_symbols_cap=get_runtime_int("TIMESERIES_SYNC_MAX_SYMBOLS", 50_000),
    )
    try:
        from app.infrastructure.timeseries.sync_snapshot import record_timeseries_sync_snapshot

        record_timeseries_sync_snapshot(result, source="celery_beat")
    except Exception as exc:
        logger.debug("celery sync snapshot skipped: %s", exc)
    return result


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
    """Paginated full-market OHLCV backfill (TDX lday → QuestDB / ClickHouse)."""
    if truncate_first:
        from app.modules.data.services.timeseries_fresh_backfill import truncate_all_timeseries_targets

        truncate_all_timeseries_targets()
    return run_timeseries_ohlcv_backfill(
        batch_size=batch_size,
        max_batches=max_batches,
        offset=offset,
        lookback_days=lookback_days,
        workers=workers,
        all_market=True,
        mode="full",
        skip_existing=False,
    )


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
        logger.info(
            "timeseries_ohlcv_full_backfill start offset=%s batch=%s max_batches=%s",
            offset,
            batch_size,
            max_batches,
        )
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
