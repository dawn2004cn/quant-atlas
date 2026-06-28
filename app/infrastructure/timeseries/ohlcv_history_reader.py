from __future__ import annotations

"""Read OHLCV bars from QuestDB / ClickHouse (env-driven table names)."""

from datetime import date
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.core.sql_safety import safe_table_name as _safe_table
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.infrastructure.timeseries.timeseries_factory import (
    create_clickhouse_adapter,
    create_questdb_adapter,
    load_clickhouse_settings,
    load_questdb_settings,
)

logger = get_logger(__name__)


def _safe_literal(value: str) -> str:
    """Escape single quotes for safe use in SQL string literals.

    Standard SQL escaping: double single quotes (' -> '').
    Input should already be normalized/validated; this is a last-resort defense.
    """
    if not isinstance(value, str):
        value = str(value)
    return value.replace("'", "''")


def _stock_code(symbol: str, market: MarketCode) -> str:
    if market == MarketCode.CN:
        return SymbolNormalizer.to_db_code(symbol, market="CN")
    return str(symbol or "").strip().upper()[:32]


def _rows_to_bars(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        td = r.get("trade_date") or r.get("date") or r.get("timestamp")
        if hasattr(td, "strftime"):
            ds = td.strftime("%Y-%m-%d")
        else:
            ds = str(td)[:10]
        if not ds or ds == "None":
            continue
        out.append(
            {
                "date": ds,
                "open": float(r.get("open") or 0),
                "high": float(r.get("high") or 0),
                "low": float(r.get("low") or 0),
                "close": float(r.get("close") or 0),
                "volume": float(r.get("volume") or 0),
                "amount": float(r.get("amount") or 0),
            }
        )
    return out


def fetch_questdb_ohlcv(
    symbol: str,
    market: MarketCode,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    if market != MarketCode.CN or load_questdb_settings() is None:
        return []
    adapter = create_questdb_adapter()
    if adapter is None or not adapter.connect():
        return []
    try:
        table = _safe_table(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
        from app.modules.data.services.questdb_table_layout import load_questdb_ohlcv_layout

        layout = load_questdb_ohlcv_layout(table)
        date_expr = layout.latest_expr() if layout else "trade_date"
        code = _stock_code(symbol, market)
        start_s = start_date.strftime("%Y-%m-%d")
        end_s = end_date.strftime("%Y-%m-%d")
        sql = (
            f"SELECT {date_expr} AS trade_date, open, high, low, close, volume, amount "
            f"FROM {table} "
            f"WHERE stock_code = '{_safe_literal(code)}' "
            f"AND {date_expr} >= '{_safe_literal(start_s)}' "
            f"AND {date_expr} <= '{_safe_literal(end_s)}' "
            f"ORDER BY {date_expr} ASC "
            f"LIMIT 10000"
        )
        rows = adapter.execute_raw_query(sql)
        bars = _rows_to_bars(rows)
        if bars:
            logger.info("QuestDB got %d bars for %s from %s", len(bars), code, table)
        return bars
    except Exception as exc:
        logger.debug("fetch_questdb_ohlcv: %s", exc)
        return []
    finally:
        adapter.disconnect()


def fetch_clickhouse_ohlcv(
    symbol: str,
    market: MarketCode,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    table_raw = (get_runtime("CLICKHOUSE_OHLCV_TABLE", "") or "").strip()
    if not table_raw or market != MarketCode.CN or load_clickhouse_settings() is None:
        return []
    adapter = create_clickhouse_adapter()
    if adapter is None or not adapter.connect():
        return []
    try:
        table = _safe_table(table_raw, "stock_history")
        code = _stock_code(symbol, market)
        start_s = start_date.strftime("%Y-%m-%d")
        end_s = end_date.strftime("%Y-%m-%d")
        sql = (
            f"SELECT trade_date, open, high, low, close, volume, amount "
            f"FROM {table} "
            f"WHERE stock_code = '{_safe_literal(code)}' "
            f"AND trade_date >= '{_safe_literal(start_s)}' "
            f"AND trade_date <= '{_safe_literal(end_s)}' "
            f"ORDER BY trade_date ASC "
            f"LIMIT 10000"
        )
        rows = adapter.execute_raw_query(sql)
        bars = _rows_to_bars(rows)
        if bars:
            logger.info("ClickHouse got %d bars for %s from %s", len(bars), code, table)
        return bars
    except Exception as exc:
        logger.debug("fetch_clickhouse_ohlcv: %s", exc)
        return []
    finally:
        adapter.disconnect()


def probe_ohlcv_tables() -> dict[str, Any]:
    """Lightweight row-count probe for configured OHLCV tables."""
    out: dict[str, Any] = {}
    q_cfg = load_questdb_settings()
    if q_cfg is not None:
        table = _safe_table(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
        adapter = create_questdb_adapter(q_cfg)
        rows = 0
        if adapter and adapter.connect():
            try:
                sample = adapter.execute_raw_query(f"SELECT count() AS cnt FROM {table}")
                if sample:
                    rows = int(sample[0].get("cnt") or 0)
                sample_sym = adapter.execute_raw_query(
                    f"SELECT count() AS cnt FROM {table} WHERE stock_code = 'sh600519'"
                )
                if sample_sym:
                    out["questdb_sample_sh600519"] = int(sample_sym[0].get("cnt") or 0)
            except Exception as exc:
                logger.debug("probe questdb table: %s", exc)
            finally:
                adapter.disconnect()
        out["questdb_table"] = table
        out["questdb_rows"] = rows

    ch_table = (get_runtime("CLICKHOUSE_OHLCV_TABLE", "") or "").strip()
    if ch_table and load_clickhouse_settings() is not None:
        table = _safe_table(ch_table, "stock_history")
        adapter = create_clickhouse_adapter()
        rows = 0
        if adapter and adapter.connect():
            try:
                sample = adapter.execute_raw_query(f"SELECT count() AS cnt FROM {table}")
                if sample:
                    rows = int(sample[0].get("cnt") or 0)
            except Exception as exc:
                logger.debug("probe clickhouse table: %s", exc)
            finally:
                adapter.disconnect()
        out["clickhouse_table"] = table
        out["clickhouse_rows"] = rows
    return out
