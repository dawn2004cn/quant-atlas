from __future__ import annotations
"""QuestDB ILP writer for OHLCV bars."""

from datetime import datetime
from typing import Any

from app.modules.data.services.ohlcv_incremental_policy import dedupe_bars_by_date
from app.modules.data.services.ohlcv_sync_common import safe_table_name
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.infrastructure.database.timeseries_settings import load_questdb_settings
from app.infrastructure.timeseries.timeseries_factory import create_questdb_adapter

logger = get_logger(__name__)


def questdb_table() -> str:
    return safe_table_name(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")


def _questdb_literal(value: str) -> str:
    """Escape a string for QuestDB SQL literals.

    QuestDB follows standard SQL: single quotes are doubled.
    """
    return "'" + str(value).replace("'", "''") + "'"


def _safe_code(code: str) -> str:
    """Validate and normalize a stock code before use in SQL."""
    import re
    if not re.match(r"^[a-z]{2}\d{6}$", code.lower()):
        raise ValueError(f"invalid stock code format: {code!r}")
    return code.lower()


def _auth_suffix(cfg: Any) -> str:
    user = (cfg.user or "").strip()
    pwd = (cfg.password or "").strip()
    if not user:
        return ""
    auth = f"username={user};"
    if pwd:
        auth += f"password={pwd};"
    return auth


def _http_conf(cfg: Any) -> str:
    return f"http::addr={cfg.host}:{cfg.http_port};{_auth_suffix(cfg)}"


def _tcp_conf(cfg: Any) -> str:
    """ILP/TCP (9009) does not support basic_auth in client conf."""
    return f"tcp::addr={cfg.host}:{cfg.ilp_port};"


def ensure_questdb_dedup(table: str | None = None) -> None:
    """QuestDB 无行级 DELETE，依赖 DEDUP UPSERT KEYS 实现幂等写入。"""
    from app.modules.data.services.questdb_table_layout import load_questdb_ohlcv_layout

    cfg = load_questdb_settings()
    if cfg is None:
        return
    tbl = table or questdb_table()
    layout = load_questdb_ohlcv_layout(tbl)
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return
    keys = ", ".join(layout.dedup_keys)
    try:
        adapter.execute_raw_query(
            f"ALTER TABLE {tbl} DEDUP ENABLE UPSERT KEYS ({keys});"
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ensure_questdb_dedup %s: %s", tbl, exc)
    finally:
        adapter.disconnect()


def delete_questdb_date_range(
    stock_code: str,
    start_date: str,
    end_date: str,
    table: str | None = None,
) -> None:
    """QuestDB 不支持 ``DELETE FROM``；全量/增量幂等靠 ``DEDUP UPSERT KEYS``（见 ``ensure_questdb_dedup``）。"""
    del stock_code, start_date, end_date, table


def write_bars_questdb(stock_code: str, bars: list[dict[str, Any]], table: str | None = None) -> int:
    cfg = load_questdb_settings()
    if cfg is None or not bars:
        return 0
    safe_code = _safe_code(stock_code)
    bars = dedupe_bars_by_date(bars)
    tbl = table or questdb_table()
    try:
        from questdb.ingress import Sender, TimestampNanos
    except ImportError:
        logger.warning("questdb ingress not available; pip install -U questdb")
        return _write_bars_questdb_http_exec(safe_code, bars, tbl, cfg)
    written = 0
    def _send(conf: str) -> int:
        n = 0
        with Sender.from_conf(conf) as sender:
            for row in bars:
                td = str(row.get("date") or row.get("trade_date") or "")[:10]
                if not td:
                    continue
                sender.row(
                    tbl,
                    symbols={"stock_code": safe_code},
                    columns={
                        "open": float(row.get("open") or 0),
                        "high": float(row.get("high") or 0),
                        "low": float(row.get("low") or 0),
                        "close": float(row.get("close") or 0),
                        "volume": float(row.get("volume") or 0),
                        "amount": float(row.get("amount") or 0),
                    },
                    at=TimestampNanos.from_datetime(datetime.fromisoformat(td)),
                )
                n += 1
            sender.flush()
        return n

    try:
        n = _send(_http_conf(cfg))
        if n > 0:
            return n
    except Exception as exc:  # noqa: BLE001
        logger.debug("write_bars_questdb http ilp %s: %s", stock_code, exc)
    try:
        n = _send(_tcp_conf(cfg))
        if n > 0:
            return n
    except Exception as exc2:  # noqa: BLE001
        logger.debug("write_bars_questdb tcp ilp %s: %s", stock_code, exc2)
    return _write_bars_questdb_http_exec(stock_code, bars, tbl, cfg)


def _ts_iso(td: str) -> str:
    return f"{td[:10]}T00:00:00.000000Z"


def _write_bars_questdb_http_exec(
    stock_code: str,
    bars: list[dict[str, Any]],
    table: str,
    cfg: Any,
) -> int:
    """PG/HTTP SQL INSERT when ILP ports are closed.

    Table name is validated via ``safe_table_name`` (called in ``questdb_table``).
    String values use standard SQL literal escaping.
    Stock code is validated via ``_safe_code`` before use.
    """
    from app.modules.data.services.questdb_table_layout import load_questdb_ohlcv_layout

    layout = load_questdb_ohlcv_layout(table)
    adapter = create_questdb_adapter(cfg)
    if adapter is None:
        return 0
    connected = adapter.connect()
    if not connected:
        import time

        for attempt in range(3):
            time.sleep(0.5 * (attempt + 1))
            if adapter.connect():
                connected = True
                break
    if not connected:
        logger.warning(
            "write_bars_questdb exec: cannot connect %s (pg:%s http:%s)",
            cfg.host,
            cfg.pg_port,
            cfg.http_port,
        )
        return 0
    written = 0
    chunk: list[str] = []
    cols = ["stock_code", layout.ts_column]
    if layout.date_column != layout.ts_column:
        cols.append(layout.date_column)
    cols.extend(["open", "high", "low", "close", "volume", "amount"])
    col_sql = ", ".join(cols)
    try:
        code_lit = _questdb_literal(stock_code)
        for row in bars:
            td = str(row.get("date") or row.get("trade_date") or "")[:10]
            if not td:
                continue
            vals = [
                code_lit,
                f"'{_ts_iso(td)}'",
            ]
            if layout.date_column != layout.ts_column:
                vals.append(_questdb_literal(td))
            vals.extend(
                str(float(row.get(k) or 0))
                for k in ("open", "high", "low", "close", "volume", "amount")
            )
            chunk.append(f"({', '.join(vals)})")
            if len(chunk) >= 100:
                sql = f"INSERT INTO {table} ({col_sql}) VALUES " + ",".join(chunk)
                adapter.execute_raw_query(sql)
                written += len(chunk)
                chunk = []
        if chunk:
            sql = f"INSERT INTO {table} ({col_sql}) VALUES " + ",".join(chunk)
            adapter.execute_raw_query(sql)
            written += len(chunk)
    except Exception as exc:  # noqa: BLE001
        logger.warning("write_bars_questdb exec %s: %s", stock_code, exc)
        return written
    finally:
        adapter.disconnect()
    if written:
        logger.info("QuestDB exec wrote %d rows for %s", written, stock_code)
    return written
