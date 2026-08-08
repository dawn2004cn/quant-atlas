from __future__ import annotations
"""Sync CN daily OHLCV into ClickHouse (HTTP INSERT)."""

from typing import Any

from app.modules.data.services.ohlcv_incremental_policy import dedupe_bars_by_date
from app.modules.data.services.ohlcv_sync_common import safe_table_name
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.infrastructure.database.timeseries_settings import load_clickhouse_settings
from app.infrastructure.timeseries.timeseries_factory import create_clickhouse_adapter

logger = get_logger(__name__)

_BATCH = 150


def _ch_table() -> str:
    return safe_table_name(get_runtime("CLICKHOUSE_OHLCV_TABLE", "stock_history"), "stock_history")


def _clickhouse_literal(value: str) -> str:
    """Properly escape a string for ClickHouse SQL literals.

    ClickHouse uses standard SQL escaping: single quotes are doubled.
    Backslashes are NOT escape characters in ClickHouse string literals
    (unless the 'backslash_escape' setting is enabled, which is off by default).
    """
    return "'" + str(value).replace("'", "''") + "'"


def _safe_code(code: str) -> str:
    """Validate and normalize a stock code before use in SQL.

    Returns the normalized code if it matches the expected pattern,
    otherwise raises ValueError to prevent injection.
    """
    import re
    if not re.match(r"^[a-z]{2}\d{6}$", code.lower()):
        raise ValueError(f"invalid stock code format: {code!r}")
    return code.lower()


def delete_clickhouse_date_range(
    stock_code: str,
    start_date: str,
    end_date: str,
    table: str | None = None,
) -> None:
    """Delete symbol rows in ``[start_date, end_date]`` before re-insert (idempotent sync).

    Table name is validated via ``safe_table_name`` (called in ``_ch_table``).
    String values use ClickHouse-safe literal escaping.
    Stock code is validated via ``_safe_code`` to prevent injection.
    """
    if load_clickhouse_settings() is None:
        return
    safe_code = _safe_code(stock_code)
    tbl = table or _ch_table()
    adapter = create_clickhouse_adapter()
    if adapter is None or not adapter.connect():
        return
    try:
        sql = (
            f"DELETE FROM {tbl} WHERE stock_code = {_clickhouse_literal(safe_code)} "
            f"AND trade_date >= toDate({_clickhouse_literal(start_date[:10])}) "
            f"AND trade_date <= toDate({_clickhouse_literal(end_date[:10])}) "
            f"SETTINGS mutations_sync = 1"
        )
        if hasattr(adapter, "execute_dml"):
            adapter.execute_dml(sql)
        else:
            adapter.execute_raw_query(sql)
    except Exception as exc:  # noqa: BLE001
        logger.debug("delete_clickhouse_date_range %s: %s", stock_code, exc)
    finally:
        adapter.disconnect()


def write_bars_clickhouse(stock_code: str, bars: list[dict[str, Any]], table: str | None = None) -> int:
    if load_clickhouse_settings() is None or not bars:
        return 0
    safe_code = _safe_code(stock_code)
    bars = dedupe_bars_by_date(bars)
    tbl = table or _ch_table()
    adapter = create_clickhouse_adapter()
    if adapter is None or not adapter.connect():
        return 0
    try:
        written = 0
        chunk: list[str] = []
        for row in bars:
            td = str(row.get("date") or row.get("trade_date") or "")[:10]
            if not td:
                continue
            chunk.append(
                f"({_clickhouse_literal(safe_code)}, {_clickhouse_literal(td)}, "
                f"{float(row.get('open') or 0)}, {float(row.get('high') or 0)}, "
                f"{float(row.get('low') or 0)}, {float(row.get('close') or 0)}, "
                f"{float(row.get('volume') or 0)}, {float(row.get('amount') or 0)})"
            )
            if len(chunk) >= _BATCH:
                sql = (
                    f"INSERT INTO {tbl} "
                    "(stock_code, trade_date, open, high, low, close, volume, amount) VALUES "
                    + ",".join(chunk)
                )
                ok = adapter.execute_dml(sql) if hasattr(adapter, "execute_dml") else bool(
                    adapter.execute_raw_query(sql)
                )
                if ok:
                    written += len(chunk)
                else:
                    logger.warning("write_bars_clickhouse %s: chunk insert failed", stock_code)
                    return written
                chunk = []
        if chunk:
            sql = (
                f"INSERT INTO {tbl} "
                "(stock_code, trade_date, open, high, low, close, volume, amount) VALUES "
                + ",".join(chunk)
            )
            ok = adapter.execute_dml(sql) if hasattr(adapter, "execute_dml") else bool(
                adapter.execute_raw_query(sql)
            )
            if ok:
                written += len(chunk)
            else:
                logger.warning("write_bars_clickhouse %s: tail insert failed", stock_code)
        return written
    except Exception as exc:  # noqa: BLE001
        logger.warning("write_bars_clickhouse %s: %s", stock_code, exc)
        return 0
    finally:
        adapter.disconnect()


def clickhouse_sync_enabled() -> bool:
    return bool((get_runtime("CLICKHOUSE_OHLCV_TABLE", "") or "").strip()) and load_clickhouse_settings() is not None
