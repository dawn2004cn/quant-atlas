from __future__ import annotations

from typing import Any

import pymysql.cursors

from app.core.utils.sql_utils import validate_identifier
from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter
from app.infrastructure.database.mysql_settings import MysqlSettings


class MySQLIntegrationProbeRepository:
    """Read-only row counts for integration stack health probes."""

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def count_tables(self, tables: tuple[tuple[str, str], ...]) -> dict[str, Any]:
        conn = self._conn_port.connect()
        result: dict[str, Any] = {}
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                for key, table in tables:
                    if not validate_identifier(table):
                        result[key] = f"error:invalid_table_name:{table}"
                        continue
                    try:
                        cur.execute(f"SELECT COUNT(*) AS c FROM `{table}`")
                        row = cur.fetchone() or {}
                        result[key] = int(row.get("c") or 0)
                    except Exception as exc:  # noqa: BLE001
                        result[key] = f"error:{type(exc).__name__}:{exc}"
        finally:
            conn.close()
        return result
