from __future__ import annotations
"""Sample TDX vs QuestDB/ClickHouse/Timescale coverage and latest trade_date."""

from datetime import date, timedelta
from typing import Any

from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe
from app.modules.data.services.tdx_ohlcv_reader import fetch_tdx_daily_bars
from app.config import get_settings
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.infrastructure.database.timeseries_settings import (
    load_clickhouse_settings,
    load_questdb_settings,
)
from app.infrastructure.timeseries.ohlcv_latest_reader import (
    batch_get_latest_dates_timescale,
    fetch_latest_trade_date_clickhouse,
    fetch_latest_trade_date_questdb,
)

logger = get_logger(__name__)


def run_ohlcv_reconciliation(*, sample_size: int | None = None) -> dict[str, Any]:
    """Compare latest bar date: TDX file vs configured stores (random head sample)."""
    if not get_runtime_bool("ENABLE_OHLCV_RECONCILIATION", True):
        return {"ok": True, "skipped": True}

    universe = get_tdx_cn_universe()
    n = sample_size or get_runtime_int("OHLCV_RECON_SAMPLE", 40)
    n = min(max(n, 5), len(universe))
    sample = universe[:n]

    want_q = load_questdb_settings() is not None
    want_ch = load_clickhouse_settings() is not None
    want_ts = get_settings().use_timescaledb

    end_d = date.today()
    start_d = end_d - timedelta(days=7)
    mismatches: list[dict[str, Any]] = []
    checked = 0

    ts_latest: dict[str, str | None] = {}
    if want_ts:
        db_codes = [SymbolNormalizer.to_db_code(SymbolNormalizer.normalize_cn_symbol(c)) for c in sample]
        ts_latest = batch_get_latest_dates_timescale(db_codes)

    for cn in sample:
        db = SymbolNormalizer.to_db_code(cn)
        tdx_bars = fetch_tdx_daily_bars(cn, start_d, end_d)
        tdx_latest = tdx_bars[-1]["date"] if tdx_bars else None
        row: dict[str, Any] = {"code": cn, "tdx_latest": tdx_latest}
        if want_q:
            qd = fetch_latest_trade_date_questdb(cn)
            row["questdb_latest"] = qd.isoformat() if qd else None
            if tdx_latest and (qd is None or qd.isoformat() < tdx_latest):
                mismatches.append({**row, "target": "questdb"})
        if want_ch:
            ch = fetch_latest_trade_date_clickhouse(cn)
            row["clickhouse_latest"] = ch.isoformat() if ch else None
            if tdx_latest and (ch is None or ch.isoformat() < tdx_latest):
                mismatches.append({**row, "target": "clickhouse"})
        if want_ts:
            row["timescale_latest"] = ts_latest.get(db)
            if tdx_latest and (not ts_latest.get(db) or (ts_latest.get(db) or "") < tdx_latest):
                mismatches.append({**row, "target": "timescale"})
        checked += 1

    out = {
        "ok": len(mismatches) == 0,
        "checked": checked,
        "universe_size": len(universe),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:30],
    }
    if mismatches:
        logger.warning("ohlcv_reconciliation: %d mismatches in sample %d", len(mismatches), checked)
    return out
