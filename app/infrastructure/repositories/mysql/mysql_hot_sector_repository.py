from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter
from app.infrastructure.database.mysql_settings import MysqlSettings


class MySQLHotSectorRepository:
    """MySQL persistence for ``em_hot_sector_*`` tables."""

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def save_ingest_batch(
        self,
        *,
        snapshot_at: str,
        trade_date: str,
        ingest_kind: str,
        snapshot_source: str,
        sector_params: list[tuple[Any, ...]],
        member_params: list[tuple[Any, ...]],
        retention_days: int,
    ) -> None:
        member_rows = len(member_params)
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO em_hot_sector_snapshots
                        (snapshot_at, trade_date, ingest_kind, sector_count, member_rows, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        snapshot_at,
                        trade_date,
                        ingest_kind,
                        len(sector_params),
                        0,
                        snapshot_source,
                    ),
                )
                if sector_params:
                    cur.executemany(
                        """
                        INSERT INTO em_hot_sectors
                            (snapshot_at, sector_code, name, kind, source,
                             change_pct, price, amount, volume, turnover_rate, rank_no)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        sector_params,
                    )
                if member_params:
                    cur.executemany(
                        """
                        INSERT INTO em_hot_sector_members
                            (snapshot_at, sector_code, symbol, name,
                             change_pct, price, amount, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        member_params,
                    )
                cur.execute(
                    """
                    UPDATE em_hot_sector_snapshots
                    SET member_rows=%s WHERE snapshot_at=%s
                    """,
                    (member_rows, snapshot_at),
                )
                self._prune_old_snapshots(cur, retention_days=retention_days)
            self._conn_port.commit(conn)
        except Exception:
            self._conn_port.rollback(conn)
            raise
        finally:
            conn.close()

    def _prune_old_snapshots(self, cur: Any, *, retention_days: int) -> None:
        days = max(1, retention_days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("DELETE FROM em_hot_sector_members WHERE snapshot_at < %s", (cutoff,))
        cur.execute("DELETE FROM em_hot_sectors WHERE snapshot_at < %s", (cutoff,))
        cur.execute("DELETE FROM em_hot_sector_snapshots WHERE snapshot_at < %s", (cutoff,))

    def list_snapshots(self, *, limit: int) -> list[dict[str, Any]]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT snapshot_at, trade_date, ingest_kind, sector_count, member_rows, source
                    FROM em_hot_sector_snapshots
                    ORDER BY snapshot_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def latest_snapshot_at(self) -> str | None:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT snapshot_at FROM em_hot_sector_snapshots ORDER BY snapshot_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                return str(row[0]) if row else None
        finally:
            conn.close()

    def list_sectors(
        self,
        *,
        snapshot_at: str,
        kind: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                k = (kind or "all").strip().lower()
                base_sql = """
                        SELECT sector_code, name, kind, source, change_pct, price, amount, volume,
                               turnover_rate, rank_no
                        FROM em_hot_sectors
                        WHERE snapshot_at=%s
                        """
                if k == "concept":
                    cur.execute(
                        base_sql + " AND kind=%s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "concept", limit),
                    )
                elif k == "industry":
                    cur.execute(
                        base_sql + " AND kind=%s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "industry", limit),
                    )
                elif k == "em":
                    cur.execute(
                        base_sql + " AND source LIKE %s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "东方财富%", limit),
                    )
                elif k == "ths":
                    cur.execute(
                        base_sql + " AND source LIKE %s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "同花顺%", limit),
                    )
                elif k == "kpl":
                    cur.execute(
                        base_sql + " AND source LIKE %s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "开盘啦%", limit),
                    )
                elif k == "xgt":
                    cur.execute(
                        base_sql + " AND source LIKE %s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "选股通%", limit),
                    )
                elif k == "region":
                    cur.execute(
                        base_sql + " AND kind=%s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "region", limit),
                    )
                elif k == "csrc":
                    cur.execute(
                        base_sql + " AND kind=%s ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, "csrc", limit),
                    )
                else:
                    cur.execute(
                        base_sql + " ORDER BY change_pct DESC LIMIT %s",
                        (snapshot_at, limit),
                    )
                cols = [c[0] for c in cur.description]
                rows: list[dict[str, Any]] = []
                for r in cur.fetchall():
                    item = dict(zip(cols, r))
                    rows.append(
                        {
                            "sector_code": item["sector_code"],
                            "name": item["name"],
                            "kind": item["kind"],
                            "source": item["source"],
                            "change_pct": float(item["change_pct"] or 0),
                            "price": float(item["price"] or 0),
                            "amount": float(item["amount"] or 0),
                            "volume": float(item["volume"] or 0),
                            "turnover_rate": float(item.get("turnover_rate") or 0),
                            "rank_no": int(item.get("rank_no") or 0),
                        }
                    )
                return rows
        finally:
            conn.close()

    def list_members(
        self,
        *,
        sector_code: str,
        snapshot_at: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT symbol, name, change_pct, price, amount, volume
                    FROM em_hot_sector_members
                    WHERE snapshot_at=%s AND sector_code=%s
                    ORDER BY change_pct DESC
                    LIMIT %s
                    """,
                    (snapshot_at, sector_code, limit),
                )
                cols = [c[0] for c in cur.description]
                rows: list[dict[str, Any]] = []
                for r in cur.fetchall():
                    item = dict(zip(cols, r))
                    sym = str(item["symbol"] or "")
                    rows.append(
                        {
                            "symbol": sym,
                            "code": sym.replace("sh", "").replace("sz", "").replace("bj", ""),
                            "name": item["name"],
                            "change_pct": float(item["change_pct"] or 0),
                            "price": float(item["price"] or 0),
                            "amount": float(item["amount"] or 0),
                            "volume": float(item["volume"] or 0),
                        }
                    )
                return rows
        finally:
            conn.close()
