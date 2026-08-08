from __future__ import annotations
"""Shared helpers: TDX → QuestDB / ClickHouse (never MySQL)."""

import re
from datetime import date
from typing import Any

from app.modules.data.services.ohlcv_incremental_policy import (
    incremental_cursor_start,
)
from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe
from app.modules.data.services.tdx_ohlcv_reader import fetch_tdx_daily_bars
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_int
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.infrastructure.timeseries.ohlcv_latest_reader import (
    fetch_min_latest_trade_date_for_targets,
    safe_table_name,
)

logger = get_logger(__name__)

_VALID_CN = re.compile(r"^(sh|sz|bj)\d{6}$", re.IGNORECASE)

__all__ = [
    "fetch_cn_daily_bars",
    "resolve_sync_symbols",
    "safe_table_name",
    "sync_limits",
    "symbol_incremental_start",
]


def resolve_sync_symbols(
    limit: int,
    symbols: list[str] | None,
    *,
    offset: int = 0,
    all_market: bool = False,
) -> list[str]:
    if symbols:
        out: list[str] = []
        for s in symbols[offset : offset + limit]:
            norm = SymbolNormalizer.normalize_cn_symbol(s)
            if _VALID_CN.match(norm):
                out.append(norm)
        return out

    csv = (get_runtime("TIMESERIES_SYNC_SYMBOLS", "") or get_runtime("QUESTDB_SYNC_SYMBOLS", "") or "").strip()
    if csv:
        items = [SymbolNormalizer.normalize_cn_symbol(s) for s in csv.split(",") if s.strip()]
        items = [c for c in items if _VALID_CN.match(c)]
        return items[offset : offset + limit]

    universe = get_tdx_cn_universe()
    if limit <= 0:
        slice_codes = universe[offset:]
    else:
        slice_codes = universe[offset : offset + limit]
    logger.info("resolve_sync_symbols: tdx universe slice %d codes (offset=%s)", len(slice_codes), offset)
    return slice_codes


def fetch_cn_daily_bars(symbol: str, start_d: date, end_d: date) -> list[dict[str, Any]]:
    """TDX lday only."""
    norm = SymbolNormalizer.normalize_cn_symbol(symbol)
    return fetch_tdx_daily_bars(norm, start_d, end_d)


def symbol_incremental_start(
    stock_code: str,
    end_d: date,
    lookback_days: int,
    *,
    want_questdb: bool,
    want_clickhouse: bool,
) -> date | None:
    """Per-symbol start: min(latest across stores) minus overlap; empty store uses lookback."""
    latest = fetch_min_latest_trade_date_for_targets(
        stock_code,
        want_questdb=want_questdb,
        want_clickhouse=want_clickhouse,
    )
    return incremental_cursor_start(latest, end_d, lookback_days)


def sync_limits(
    *,
    limit: int | None,
    lookback_days: int | None,
    max_symbols_cap: int = 2000,
    all_market: bool = False,
) -> tuple[int, int]:
    default_lim = get_runtime_int("TIMESERIES_SYNC_LIMIT", get_runtime_int("QUESTDB_SYNC_LIMIT", 500))
    if limit is not None and limit <= 0:
        lim = min(len(get_tdx_cn_universe()), max_symbols_cap)
    elif limit is not None and limit > 0:
        lim = min(limit, max_symbols_cap)
    elif all_market:
        lim = min(len(get_tdx_cn_universe()), max_symbols_cap)
    else:
        lim = min(max(default_lim, 1), max_symbols_cap)
    days = max(
        lookback_days
        or get_runtime_int("TIMESERIES_SYNC_LOOKBACK_DAYS", get_runtime_int("QUESTDB_SYNC_LOOKBACK_DAYS", 1500)),
        30,
    )
    return lim, days
