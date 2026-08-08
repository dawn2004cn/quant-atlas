from __future__ import annotations
"""QuestDB / ClickHouse / Timescale 日 K 覆盖快照，用于回填前验收与收尾对账。"""

from typing import Any

from app.modules.data.services.ohlcv_reconciliation_service import run_ohlcv_reconciliation
from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe
from app.config import get_settings
from app.core.runtime_config import get_runtime
from app.core.sql_safety import safe_table_name
from app.infrastructure.database.postgres_client import postgres_connect, ping_postgres
from app.infrastructure.database.timeseries_settings import (
    load_clickhouse_settings,
    load_questdb_settings,
)
from app.infrastructure.timeseries.timeseries_factory import (
    create_clickhouse_adapter,
    create_questdb_adapter,
)


def _questdb_snapshot() -> dict[str, Any]:
    cfg = load_questdb_settings()
    if cfg is None:
        return {"enabled": False}
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return {"enabled": True, "connected": False}
    try:
        table = safe_table_name(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
        rows = adapter.execute_raw_query(f"SELECT count() AS n FROM {table}")
        sample = adapter.execute_raw_query(
            f"SELECT count() AS n FROM {table} WHERE stock_code = 'sh600519'"
        )
        return {
            "enabled": True,
            "connected": True,
            "table": table,
            "rows": int((rows[0] or {}).get("n") or 0) if rows else 0,
            "sample_sh600519": int((sample[0] or {}).get("n") or 0) if sample else 0,
        }
    finally:
        adapter.disconnect()


def _clickhouse_snapshot() -> dict[str, Any]:
    cfg = load_clickhouse_settings()
    if cfg is None:
        return {"enabled": False}
    adapter = create_clickhouse_adapter(cfg)
    if adapter is None or not adapter.connect():
        return {"enabled": True, "connected": False}
    try:
        table = safe_table_name(get_runtime("CLICKHOUSE_OHLCV_TABLE", "stock_history"), "stock_history")
        rows = adapter.execute_raw_query(f"SELECT count() AS n FROM {table}")
        sample = adapter.execute_raw_query(
            f"SELECT count() AS n FROM {table} WHERE stock_code = 'sh600519'"
        )
        return {
            "enabled": True,
            "connected": True,
            "table": table,
            "rows": int((rows[0] or {}).get("n") or 0) if rows else 0,
            "sample_sh600519": int((sample[0] or {}).get("n") or 0) if sample else 0,
        }
    finally:
        adapter.disconnect()


def _timescale_snapshot(*, exact_count: bool = False) -> dict[str, Any]:
    settings = get_settings()
    if not settings.use_timescaledb or settings.postgres is None:
        return {"enabled": False}
    pg = settings.postgres
    if not ping_postgres(pg):
        return {"enabled": True, "connected": False}
    out: dict[str, Any] = {"enabled": True, "connected": True}
    with postgres_connect(pg, autocommit=True) as conn:
        with conn.cursor() as cur:
            if exact_count:
                cur.execute("SELECT count(*), count(DISTINCT symbol) FROM market_bars")
                row = cur.fetchone()
                out["rows"] = int(row[0] or 0)
                out["symbols"] = int(row[1] or 0)
            else:
                cur.execute(
                    "SELECT reltuples::bigint FROM pg_class WHERE relname = 'market_bars'"
                )
                est = cur.fetchone()
                out["rows_est"] = int(est[0] or 0) if est else None
                cur.execute(
                    "SELECT n_live_tup FROM pg_stat_all_tables WHERE relname = 'market_bars'"
                )
                stat = cur.fetchone()
                out["symbols_est"] = int(stat[0] or 0) if stat else None
            cur.execute(
                "SELECT count(*) FROM market_bars WHERE symbol = 'sh600519'"
            )
            out["sample_sh600519"] = int(cur.fetchone()[0] or 0)
    return out


def collect_timeseries_sync_status(*, exact_timescale_count: bool = False) -> dict[str, Any]:
    """Return row/symbol coverage for TDX universe vs three stores."""
    universe = get_tdx_cn_universe()
    questdb = _questdb_snapshot()
    clickhouse = _clickhouse_snapshot()
    timescale = _timescale_snapshot(exact_count=exact_timescale_count)

    q_rows = int(questdb.get("rows") or 0)
    ch_rows = int(clickhouse.get("rows") or 0)
    ts_sample = int(timescale.get("sample_sh600519") or 0)
    ts_rows = int(timescale.get("rows") or timescale.get("rows_est") or 0)
    target_rows = max(q_rows, ch_rows, 1_000_000)

    pending: list[str] = []
    if questdb.get("enabled") and not questdb.get("connected"):
        pending.append("questdb_unreachable")
    elif questdb.get("enabled") and q_rows < 1_000_000:
        pending.append("questdb_backfill")
    if clickhouse.get("enabled") and not clickhouse.get("connected"):
        pending.append("clickhouse_unreachable")
    elif clickhouse.get("enabled") and clickhouse.get("connected") and ch_rows < target_rows * 0.98:
        pending.append("clickhouse_backfill")
    if timescale.get("enabled") and not timescale.get("connected"):
        pending.append("timescale_unreachable")
    elif timescale.get("enabled") and timescale.get("connected"):
        if ts_rows < target_rows * 0.9 and ts_sample < 500:
            pending.append("timescale_backfill")

    return {
        "ok": not pending,
        "universe_size": len(universe),
        "questdb": questdb,
        "clickhouse": clickhouse,
        "timescale": timescale,
        "pending_actions": pending,
    }


def run_timeseries_verify(*, sample_size: int | None = None) -> dict[str, Any]:
    """Coverage snapshot + latest-date reconciliation sample."""
    status = collect_timeseries_sync_status()
    recon = run_ohlcv_reconciliation(sample_size=sample_size)
    return {
        "ok": bool(status.get("ok")) and bool(recon.get("ok")),
        "status": status,
        "reconciliation": recon,
    }
