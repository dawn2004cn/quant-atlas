from __future__ import annotations

"""Latest trade_date per symbol from QuestDB / ClickHouse / Timescale."""

import re
from datetime import date

from app.config import get_settings
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.core.sql_safety import safe_table_name
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.infrastructure.database.timeseries_settings import (
    load_clickhouse_settings,
    load_questdb_settings,
)
from app.infrastructure.timeseries.timeseries_factory import (
    create_clickhouse_adapter,
    create_questdb_adapter,
)

logger = get_logger(__name__)

_VALID_CODE = re.compile(r"^(sh|sz|bj)\d{6}$", re.IGNORECASE)

def _escape_literal(value: str) -> str:
    """Escape a string for safe inclusion in SQL literals.

    Doubles single quotes and escapes backslashes for ClickHouse/QuestDB/MySQL.
    """
    return str(value).replace("\\", "\\\\").replace("'", "''")


def _safe_code(code: str) -> str:
    """Validate stock code format before use in SQL.

    Returns normalized code if valid, empty string otherwise.
    """
    norm = _norm_code(code)
    if not norm:
        raise ValueError(f"invalid stock code format: {code!r}")
    return norm


def _norm_code(symbol: str) -> str:
    norm = SymbolNormalizer.normalize_cn_symbol(symbol)
    if not _VALID_CODE.match(norm):
        return ""
    return norm


def fetch_latest_trade_date_questdb(stock_code: str) -> date | None:
    cfg = load_questdb_settings()
    if cfg is None:
        return None
    code = _safe_code(stock_code)
    if not code:
        return None
    table = safe_table_name(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
    from app.modules.data.services.questdb_table_layout import load_questdb_ohlcv_layout

    layout = load_questdb_ohlcv_layout(table)
    date_expr = layout.latest_expr() if layout else "trade_date"
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return None
    try:
        sql = (
            f"SELECT max({date_expr}) AS latest FROM {table} "
            f"WHERE stock_code = '{_escape_literal(code)}'"
        )
        rows = adapter.execute_raw_query(sql)
        if not rows:
            return None
        raw = rows[0].get("latest")
        if raw is None:
            return None
        return date.fromisoformat(str(raw)[:10])
    except Exception as exc:
        logger.debug("fetch_latest_trade_date_questdb %s: %s", code, exc)
        return None
    finally:
        adapter.disconnect()


def fetch_latest_trade_date_clickhouse(stock_code: str) -> date | None:
    if load_clickhouse_settings() is None:
        return None
    code = _safe_code(stock_code)
    if not code:
        return None
    table = safe_table_name(get_runtime("CLICKHOUSE_OHLCV_TABLE", "stock_history"), "stock_history")
    adapter = create_clickhouse_adapter()
    if adapter is None or not adapter.connect():
        return None
    try:
        sql = (
            f"SELECT max(trade_date) AS latest FROM {table} "
            f"WHERE stock_code = '{_escape_literal(code)}'"
        )
        rows = adapter.execute_raw_query(sql)
        if not rows:
            return None
        raw = rows[0].get("latest")
        if raw is None:
            return None
        return date.fromisoformat(str(raw)[:10])
    except Exception as exc:
        logger.debug("fetch_latest_trade_date_clickhouse %s: %s", code, exc)
        return None
    finally:
        adapter.disconnect()


def fetch_latest_trade_date_for_targets(
    stock_code: str,
    *,
    want_questdb: bool,
    want_clickhouse: bool,
) -> date | None:
    """Single-store latest (legacy)."""
    dates: list[date] = []
    if want_clickhouse:
        ch = fetch_latest_trade_date_clickhouse(stock_code)
        if ch is not None:
            dates.append(ch)
    if want_questdb:
        q = fetch_latest_trade_date_questdb(stock_code)
        if q is not None:
            dates.append(q)
    if not dates:
        return None
    return max(dates)


def fetch_min_latest_trade_date_for_targets(
    stock_code: str,
    *,
    want_questdb: bool,
    want_clickhouse: bool,
) -> date | None:
    """Min ``max(trade_date)`` across enabled stores — incremental starts from lagging store."""
    dates: list[date] = []
    if want_clickhouse:
        ch = fetch_latest_trade_date_clickhouse(stock_code)
        if ch is not None:
            dates.append(ch)
    if want_questdb:
        q = fetch_latest_trade_date_questdb(stock_code)
        if q is not None:
            dates.append(q)
    if not dates:
        return None
    return min(dates)


def batch_get_latest_dates_timescale(stock_codes: list[str]) -> dict[str, str | None]:
    """``stock_code`` (db form) → ``YYYY-MM-DD`` latest bar in ``market_bars``."""
    settings = get_settings()
    if not settings.use_timescaledb or not stock_codes:
        return {}

    from app.infrastructure.database.postgres_client import postgres_connect

    pg = settings.postgres
    if pg is None:
        return {}

    symbols = list({c for c in stock_codes if c})
    out: dict[str, str | None] = {s: None for s in symbols}
    try:
        conn = postgres_connect(pg, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, MAX(time::date) AS latest
                FROM market_bars
                WHERE market = %s AND symbol = ANY(%s)
                GROUP BY symbol
                """,
                ("CN", symbols),
            )
            for row in cur.fetchall():
                sym, latest = row[0], row[1]
                if latest is not None:
                    out[str(sym)] = latest.isoformat() if hasattr(latest, "isoformat") else str(latest)[:10]
        conn.close()
    except Exception as exc:
        logger.warning("batch_get_latest_dates_timescale: %s", exc)
    return out
