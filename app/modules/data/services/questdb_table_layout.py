from __future__ import annotations
"""Resolve QuestDB OHLCV table column names (legacy vs trade_date DDL)."""

from dataclasses import dataclass
import threading
from typing import Any

_layout_lock = threading.Lock()
_layout_ok: dict[str, QuestDBOhlcvLayout] = {}

from app.modules.data.services.ohlcv_sync_common import safe_table_name
from app.core.runtime_config import get_runtime
from app.core.logger import get_logger
from app.infrastructure.database.timeseries_settings import load_questdb_settings
from app.infrastructure.timeseries.timeseries_factory import create_questdb_adapter

logger = get_logger(__name__)


@dataclass(frozen=True)
class QuestDBOhlcvLayout:
    table: str
    ts_column: str
    date_column: str
    dedup_keys: tuple[str, ...]

    def latest_expr(self) -> str:
        if self.date_column != self.ts_column:
            return f"coalesce({self.date_column}, cast({self.ts_column} as date))"
        return self.ts_column


def _legacy_layout_fallback(table: str) -> QuestDBOhlcvLayout:
    """localhost 等环境常见旧表：``date`` + designated ``timestamp``。"""
    return QuestDBOhlcvLayout(
        table=table,
        ts_column="timestamp",
        date_column="date",
        dedup_keys=("timestamp", "stock_code"),
    )


def _probe_questdb_layout(table: str) -> QuestDBOhlcvLayout | None:
    cfg = load_questdb_settings()
    if cfg is None:
        return None
    tbl = safe_table_name(table, "stock_history")
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return None
    try:
        rows = adapter.execute_raw_query(f"SHOW COLUMNS FROM {tbl}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_questdb_ohlcv_layout %s: %s", tbl, exc)
        return None
    finally:
        adapter.disconnect()

    names = {str(r.get("column") or "") for r in rows}
    designated = [
        str(r.get("column") or "")
        for r in rows
        if r.get("designated") in (True, "true", "t")
    ]
    ts_col = designated[0] if designated else "timestamp"
    if "trade_date" in names:
        date_col = "trade_date"
        if ts_col not in names:
            ts_col = "trade_date"
    elif "date" in names:
        date_col = "date"
    else:
        date_col = ts_col
    dedup = tuple(k for k in (ts_col, "stock_code") if k in names)
    if len(dedup) < 2:
        dedup = ("timestamp", "stock_code") if "timestamp" in names else ("trade_date", "stock_code")
    return QuestDBOhlcvLayout(table=tbl, ts_column=ts_col, date_column=date_col, dedup_keys=dedup)


def load_questdb_ohlcv_layout(table: str | None = None) -> QuestDBOhlcvLayout:
    tbl = safe_table_name(table or get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
    with _layout_lock:
        if tbl in _layout_ok:
            return _layout_ok[tbl]
        layout = _probe_questdb_layout(tbl) or _legacy_layout_fallback(tbl)
        _layout_ok[tbl] = layout
        return layout
