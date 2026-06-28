from __future__ import annotations

"""MySQL repository for TDX gpcw financial data."""


import json
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.domain.ports.tdx_gpcw_port import TdxGpcwRepository

from ....config import get_settings
from ...database.mysql_client import mysql_get_connection
from ...database.mysql_settings import MysqlSettings

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class MySQLTdxGpcwRepository(TdxGpcwRepository):
    def __init__(self, mysql: MysqlSettings | None = None) -> None:
        self._mysql = mysql

    def _resolve_mysql(self) -> MysqlSettings | None:
        if self._mysql is not None:
            return self._mysql
        s = get_settings()
        return s.mysql if s.use_mysql else None

    def table_exists(self) -> bool:
        mysql = self._resolve_mysql()
        conn = mysql_get_connection(mysql, autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(1) FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = 'tdx_gpcw_financial'",
                    (mysql.database if mysql else "quant_atlas",),
                )
                return bool(cur.fetchone())
        finally:
            conn.close()

    def create_table(self) -> None:
        mysql = self._resolve_mysql()
        conn = mysql_get_connection(mysql, autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tdx_gpcw_financial (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        code VARCHAR(8) NOT NULL,
                        indexed_code VARCHAR(32) NOT NULL,
                        market VARCHAR(8) NOT NULL,
                        report_date INT NOT NULL,
                        source_file VARCHAR(32) NOT NULL,
                        payload_json TEXT NOT NULL,
                        non_zero_count INT DEFAULT 0,
                        imported_at VARCHAR(64) NOT NULL,
                        UNIQUE KEY uix_code_report_date (code, report_date),
                        INDEX idx_code (code),
                        INDEX idx_indexed_code (indexed_code),
                        INDEX idx_market (market),
                        INDEX idx_report_date (report_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            conn.commit()
            logger.info("tdx_gpcw_financial table created")
        finally:
            conn.close()

    def upsert_period(self, code: str, indexed_code: str, market: str, report_date: int, source_file: str, payload: dict[str, Any]) -> bool:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                non_zero = sum(1 for v in payload.values() if isinstance(v, (int, float)) and abs(v) > 0.0001)
                payload_json = json.dumps(payload, ensure_ascii=False, default=str)
                cur.execute(
                    """
                    INSERT INTO tdx_gpcw_financial
                    (code, indexed_code, market, report_date, source_file, payload_json, non_zero_count, imported_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        source_file = VALUES(source_file),
                        payload_json = VALUES(payload_json),
                        non_zero_count = VALUES(non_zero_count),
                        imported_at = VALUES(imported_at)
                    """,
                    (code, indexed_code, market, report_date, source_file, payload_json, non_zero, _utc_now()),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    def upsert_batch(self, rows: list[dict[str, Any]], batch_size: int = 50) -> tuple[int, int, int]:
        written, updated, errors = 0, 0, 0
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                for chunk in [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]:
                    for row in chunk:
                        try:
                            non_zero = sum(
                                1 for v in row.get("fields", {}).values()
                                if isinstance(v, (int, float)) and abs(v) > 0.0001
                            )
                            payload_json = json.dumps(
                                row["fields"], ensure_ascii=False, default=str
                            )
                            cur.execute(
                                """
                                INSERT INTO tdx_gpcw_financial
                                (code, indexed_code, market, report_date, source_file, payload_json, non_zero_count, imported_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    source_file = VALUES(source_file),
                                    payload_json = VALUES(payload_json),
                                    non_zero_count = VALUES(non_zero_count),
                                    imported_at = VALUES(imported_at)
                                """,
                                (
                                    row["code"],
                                    row["indexed_code"],
                                    row["market"],
                                    row["report_date"],
                                    row["source_file"],
                                    payload_json,
                                    non_zero,
                                    _utc_now(),
                                ),
                            )
                            if cur.rowcount >= 1:
                                updated += 1
                            written += 1
                        except Exception as exc:
                            errors += 1
                            logger.debug("skip row %s: %s", row.get("code"), exc)
            conn.commit()
        finally:
            conn.close()
        return written, updated, errors

    def get_stock_periods(self, code: str) -> list[dict[str, Any]]:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT indexed_code, market, report_date, source_file, non_zero_count, imported_at "
                    "FROM tdx_gpcw_financial WHERE code = %s ORDER BY report_date DESC",
                    (code,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "indexed_code": r[0],
                        "market": r[1],
                        "report_date": r[2],
                        "source_file": r[3],
                        "non_zero_count": r[4],
                        "imported_at": r[5],
                    }
                    for r in rows
                ]
        finally:
            conn.close()

    def get_stock_data(self, code: str, report_date: int) -> dict[str, Any] | None:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload_json FROM tdx_gpcw_financial "
                    "WHERE code = %s AND report_date = %s",
                    (code, report_date),
                )
                row = cur.fetchone()
                if row:
                    return json.loads(row[0])
                return None
        finally:
            conn.close()

    def get_stock_data_by_indexed_code(self, indexed_code: str, report_date: int) -> dict[str, Any] | None:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload_json FROM tdx_gpcw_financial "
                    "WHERE indexed_code = %s AND report_date = %s",
                    (indexed_code, report_date),
                )
                row = cur.fetchone()
                if row:
                    return json.loads(row[0])
                return None
        finally:
            conn.close()

    def count_rows(self) -> int:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(1) AS n FROM tdx_gpcw_financial")
                return cur.fetchone()[0]
        finally:
            conn.close()

    def count_stocks(self) -> int:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT code) AS n FROM tdx_gpcw_financial")
                return cur.fetchone()[0]
        finally:
            conn.close()

    def record_audit(
        self,
        task_type: str,
        source_file: str,
        report_date: int | None,
        stocks_processed: int,
        rows_written: int,
        rows_skipped: int,
        rows_updated: int,
        status: str,
        error_msg: str | None,
        duration_sec: float,
    ) -> None:
        conn = mysql_get_connection(self._resolve_mysql(), autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tdx_gpcw_audit
                    (task_type, source_file, report_date, stocks_processed,
                     rows_written, rows_skipped, rows_updated, status, error_msg,
                     started_at, finished_at, duration_sec)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_type,
                        source_file,
                        report_date,
                        stocks_processed,
                        rows_written,
                        rows_skipped,
                        rows_updated,
                        status,
                        error_msg,
                        _utc_now(),
                        _utc_now(),
                        duration_sec,
                    ),
                )
            conn.commit()
        finally:
            conn.close()


class NullTdxGpcwRepository(TdxGpcwRepository):
    """No-op implementation when MySQL is disabled."""

    def get_stock_periods(self, code: str) -> list[dict[str, Any]]:
        return []

    def get_stock_data(self, code: str, report_date: int) -> dict[str, Any] | None:
        return None

    def get_stock_data_by_indexed_code(
        self, indexed_code: str, report_date: int
    ) -> dict[str, Any] | None:
        return None

    def table_exists(self) -> bool:
        return False

    def count_rows(self) -> int:
        return 0

    def count_stocks(self) -> int:
        return 0
