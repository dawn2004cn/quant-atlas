from __future__ import annotations
"""QuestDB OHLCV sync entry (delegates to unified timeseries sync)."""

from typing import Any

from app.modules.data.services.timeseries_ohlcv_sync_service import run_timeseries_ohlcv_sync


def run_questdb_ohlcv_sync(
    *,
    limit: int | None = None,
    symbols: list[str] | None = None,
    lookback_days: int | None = None,
) -> dict[str, Any]:
    """Backward-compatible entry: sync QuestDB (+ ClickHouse if configured)."""
    return run_timeseries_ohlcv_sync(
        limit=limit,
        symbols=symbols,
        lookback_days=lookback_days,
    )
