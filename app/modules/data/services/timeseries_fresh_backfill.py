from __future__ import annotations
"""Truncate OHLCV timeseries tables before a full TDX re-backfill."""

from typing import Any

from app.modules.data.services.ohlcv_sync_common import safe_table_name
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool
from app.infrastructure.database.timeseries_settings import (
    load_clickhouse_settings,
    load_questdb_settings,
)
from app.infrastructure.timeseries.timeseries_factory import (
    create_clickhouse_adapter,
    create_questdb_adapter,
)

logger = get_logger(__name__)


def truncate_questdb_ohlcv() -> dict[str, Any]:
    cfg = load_questdb_settings()
    if cfg is None:
        return {"ok": True, "skipped": True, "reason": "questdb_disabled"}
    table = safe_table_name(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return {"ok": False, "error": "questdb_connect_failed"}
    try:
        adapter.execute_raw_query(f"TRUNCATE TABLE {table}")
        return {"ok": True, "table": table}
    except Exception as exc:  # noqa: BLE001
        logger.warning("truncate_questdb_ohlcv: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}
    finally:
        adapter.disconnect()


def truncate_clickhouse_ohlcv() -> dict[str, Any]:
    if get_runtime_bool("FULL_BACKFILL_SKIP_CLICKHOUSE", False):
        return {"ok": True, "skipped": True, "reason": "FULL_BACKFILL_SKIP_CLICKHOUSE"}
    cfg = load_clickhouse_settings()
    if cfg is None:
        return {"ok": True, "skipped": True, "reason": "clickhouse_disabled"}
    table = safe_table_name(get_runtime("CLICKHOUSE_OHLCV_TABLE", "stock_history"), "stock_history")
    adapter = create_clickhouse_adapter(cfg)
    if adapter is None or not adapter.connect():
        return {"ok": False, "error": "clickhouse_connect_failed"}
    try:
        adapter.execute_raw_query(f"TRUNCATE TABLE {table}")
        return {"ok": True, "table": table}
    except Exception as exc:  # noqa: BLE001
        logger.warning("truncate_clickhouse_ohlcv: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}
    finally:
        adapter.disconnect()


def truncate_timescale_ohlcv() -> dict[str, Any]:
    from app.config import get_settings
    from app.infrastructure.database.postgres_client import postgres_connect

    settings = get_settings()
    if not settings.use_timescaledb or settings.postgres is None:
        return {"ok": True, "skipped": True, "reason": "timescale_disabled"}
    tables = (
        "market_bars",
        "market_adjustment_factors",
        "market_bars_qfq",
        "market_bars_hfq",
    )
    conn = postgres_connect(settings.postgres, autocommit=True)
    cur = conn.cursor()
    truncated: list[str] = []
    errors: list[str] = []
    try:
        for tbl in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE")
                truncated.append(tbl)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{tbl}: {exc}")
        ok = not errors or len(truncated) > 0
        return {"ok": ok, "truncated": truncated, "errors": errors}
    finally:
        cur.close()
        conn.close()


def truncate_all_timeseries_targets() -> dict[str, Any]:
    """Clear QuestDB / ClickHouse / Timescale OHLCV before full re-backfill."""
    out = {
        "questdb": truncate_questdb_ohlcv(),
        "clickhouse": truncate_clickhouse_ohlcv(),
        "timescale": truncate_timescale_ohlcv(),
    }
    out["ok"] = all(
        bool(v.get("ok")) or bool(v.get("skipped"))
        for v in out.values()
        if isinstance(v, dict)
    )
    return out


def preflight_timeseries_targets(*, require_questdb: bool = True) -> dict[str, Any]:
    """Verify QuestDB + ClickHouse SQL auth before long backfill."""
    results: dict[str, Any] = {}
    q = create_questdb_adapter()
    if q is not None and q.connect():
        rows = q.execute_raw_query("SELECT count() AS n FROM stock_history")
        results["questdb"] = {"connected": True, "rows": rows[0].get("n") if rows else None}
        q.disconnect()
    else:
        results["questdb"] = {"connected": False}

    ch = create_clickhouse_adapter()
    if ch is not None and ch.connect():
        rows = ch.execute_raw_query("SELECT count() AS n FROM stock_history")
        results["clickhouse"] = {"connected": True, "rows": rows[0].get("n") if rows else None}
        ch.disconnect()
    else:
        results["clickhouse"] = {"connected": False}

    skip_ch = get_runtime_bool("FULL_BACKFILL_SKIP_CLICKHOUSE", False)
    ch_required = (
        not skip_ch
        and get_runtime_bool("ENABLE_CLICKHOUSE", True)
        and load_clickhouse_settings() is not None
    )
    q_ok = bool(results.get("questdb", {}).get("connected"))
    ch_ok = bool(results.get("clickhouse", {}).get("connected"))
    if require_questdb:
        results["ok"] = q_ok
        if ch_required:
            results["ok"] = results["ok"] and ch_ok
    else:
        results["ok"] = ch_ok if ch_required else True
    if skip_ch:
        results["clickhouse_skipped"] = True
    return results
