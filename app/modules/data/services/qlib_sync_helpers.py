from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from app.core.logger import get_logger
from app.core.utils.sql_utils import quote_identifier, validate_identifier
from app.domain.dto.service_result import GenericResponseDTO

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

_QLIB_HISTORY_TABLES = (
    "stock_history_sh_new",
    "stock_history_sz_new",
    "stock_history_bj_new",
    "stock_history_sh",
    "stock_history_sz",
    "stock_history_bj",
)


def _safe_history_table_sql(table: str) -> str | None:
    if table not in _QLIB_HISTORY_TABLES or not validate_identifier(table):
        logger.warning("Skipping invalid qlib history table: %s", table)
        return None
    return quote_identifier(table)


@dataclass
class QlibIngestMeta:
    last_ingest_at: str = ""
    market: str = "CN"
    instruments: list[str] | None = None
    date_min: str = ""
    date_max: str = ""
    row_counts: dict[str, int] | None = None
    evidence_notes: list[str] | None = None

    def to_dict(self) -> GenericResponseDTO:
        return asdict(self)


def _list_all_stock_codes_from_mysql(repo, limit: int | None = None) -> list[str]:
    """从所有 MySQL history 表获取股票代码（优先 *_new 表）。"""
    all_codes: set[str] = set()
    conn = repo._conn_port.connect()
    try:
        with conn.cursor() as cur:
            # 优先查询 *_new 表
            for tbl in _QLIB_HISTORY_TABLES[:3]:
                safe_tbl = _safe_history_table_sql(tbl)
                if not safe_tbl:
                    continue
                try:
                    cur.execute(f"SELECT DISTINCT stock_code FROM {safe_tbl}")
                    for row in cur.fetchall():
                        if row[0]:
                            all_codes.add(str(row[0]))
                except Exception:
                    logger.warning("Suppressed exception", exc_info=True)
            for tbl in _QLIB_HISTORY_TABLES[3:]:
                safe_tbl = _safe_history_table_sql(tbl)
                if not safe_tbl:
                    continue
                try:
                    cur.execute(f"SELECT DISTINCT stock_code FROM {safe_tbl}")
                    for row in cur.fetchall():
                        if row[0]:
                            all_codes.add(str(row[0]))
                except Exception:
                    logger.warning("Suppressed exception", exc_info=True)
    finally:
        conn.close()
    result = sorted(all_codes)
    if limit is not None and limit > 0:
        result = result[:limit]
    return result


def _timescale_bars_to_history_rows(ts_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for r in ts_rows:
        t = r.get("time")
        if hasattr(t, "strftime"):
            ds = t.strftime("%Y-%m-%d")
        else:
            ds = str(t)[:10]
        if not ds:
            continue
        by_date[ds] = {
            "date": ds,
            "open": float(r.get("open") or 0),
            "high": float(r.get("high") or 0),
            "low": float(r.get("low") or 0),
            "close": float(r.get("close") or 0),
            "volume": int(float(r.get("volume") or 0)),
            "amount": int(float(r.get("amount") or 0)),
        }
    return by_date