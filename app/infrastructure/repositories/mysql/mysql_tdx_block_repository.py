from __future__ import annotations

from typing import Any

from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter
from app.infrastructure.database.mysql_settings import MysqlSettings


class MySQLTdxBlockRepository:
    """MySQL read access for ``tdx_blocks`` / ``tdx_block_items``."""

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def load_membership_index(self, block_kind: str) -> dict[tuple[str, str], list[str]]:
        conn = self._conn_port.connect()
        index: dict[tuple[str, str], list[str]] = {}
        try:
            with conn.cursor() as cur:
                if block_kind:
                    cur.execute(
                        """
                        SELECT block_kind, block_name, symbol
                        FROM tdx_block_items
                        WHERE block_kind=%s
                        ORDER BY block_kind, block_name, symbol
                        """,
                        (block_kind,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT block_kind, block_name, symbol
                        FROM tdx_block_items
                        ORDER BY block_kind, block_name, symbol
                        """
                    )
                for kind, name, sym in cur.fetchall():
                    key = (str(kind or "").strip().lower(), str(name or "").strip())
                    s = str(sym or "")
                    norm = s.split(":", 1)[1] if ":" in s else s
                    if not norm:
                        continue
                    index.setdefault(key, []).append(norm)
        finally:
            conn.close()
        return index

    def list_blocks_meta(self, *, block_kind: str, limit: int) -> list[dict[str, Any]]:
        kind = (block_kind or "").strip().lower()
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                if kind:
                    cur.execute(
                        """
                        SELECT b.block_kind, b.block_name, b.updated_at,
                               COALESCE(c.cnt, 0) AS member_count
                        FROM tdx_blocks b
                        LEFT JOIN (
                            SELECT block_kind, block_name, COUNT(*) AS cnt
                            FROM tdx_block_items
                            GROUP BY block_kind, block_name
                        ) c ON c.block_kind = b.block_kind AND c.block_name = b.block_name
                        WHERE b.block_kind=%s
                        ORDER BY b.block_name
                        LIMIT %s
                        """,
                        (kind, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT b.block_kind, b.block_name, b.updated_at,
                               COALESCE(c.cnt, 0) AS member_count
                        FROM tdx_blocks b
                        LEFT JOIN (
                            SELECT block_kind, block_name, COUNT(*) AS cnt
                            FROM tdx_block_items
                            GROUP BY block_kind, block_name
                        ) c ON c.block_kind = b.block_kind AND c.block_name = b.block_name
                        ORDER BY b.block_kind, b.block_name
                        LIMIT %s
                        """,
                        (limit,),
                    )
                return [
                    {
                        "block_kind": r[0],
                        "block_name": r[1],
                        "updated_at": r[2],
                        "member_count_total": int(r[3] or 0),
                    }
                    for r in cur.fetchall()
                ]
        finally:
            conn.close()

    def load_members_bulk(
        self,
        block_keys: list[tuple[str, str]],
        *,
        per_block_limit: int,
    ) -> dict[tuple[str, str], list[dict[str, str]]]:
        if not block_keys:
            return {}
        clauses: list[str] = []
        params: list[object] = []
        for kind, name in block_keys:
            clauses.append("(i.block_kind=%s AND i.block_name=%s)")
            params.extend([kind, name])

        sql = f"""
            SELECT i.block_kind, i.block_name, i.symbol, COALESCE(b.name, '')
            FROM tdx_block_items i
            LEFT JOIN cn_stock_basics b ON b.symbol = i.symbol
            WHERE {' OR '.join(clauses)}
            ORDER BY i.block_kind, i.block_name, i.symbol
        """
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {k: [] for k in block_keys}
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                for kind, name, sym, stock_name in cur.fetchall():
                    key = (str(kind or "").strip().lower(), str(name or "").strip())
                    bucket = grouped.get(key)
                    if bucket is None or len(bucket) >= per_block_limit:
                        continue
                    s = str(sym or "")
                    norm = s.split(":", 1)[1] if ":" in s else s
                    bucket.append({"symbol": norm, "name": str(stock_name or "")})
        finally:
            conn.close()
        return grouped

    def list_blocks_simple(self, *, block_kind: str | None = None) -> list[dict[str, Any]]:
        kind = (block_kind or "").strip().lower() or None
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                if kind:
                    cur.execute(
                        """
                        SELECT block_kind, block_name, updated_at
                        FROM tdx_blocks
                        WHERE block_kind=%s
                        ORDER BY block_name
                        """,
                        (kind,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT block_kind, block_name, updated_at
                        FROM tdx_blocks
                        ORDER BY block_kind, block_name
                        """
                    )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def list_symbol_blocks(self, symbols: list[str]) -> list[dict[str, Any]]:
        if not symbols:
            return []
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(symbols))
                cur.execute(
                    f"""
                    SELECT block_kind, block_name, updated_at
                    FROM tdx_block_items
                    WHERE symbol IN ({placeholders})
                    ORDER BY block_kind, block_name
                    """,
                    tuple(symbols),
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def list_watchlists(self) -> list[dict[str, Any]]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT name, source_path, updated_at FROM tdx_watchlists ORDER BY name")
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def list_watchlist_members(self, *, watchlist_name: str) -> list[dict[str, Any]]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT i.symbol, b.name
                    FROM tdx_watchlist_items i
                    LEFT JOIN cn_stock_basics b ON b.symbol = i.symbol
                    WHERE i.watchlist_name=%s
                    ORDER BY i.symbol
                    """,
                    (watchlist_name,),
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_latest_finance_snapshot(self, symbol: str) -> dict[str, Any] | None:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM cn_finance_snapshots
                    WHERE symbol=%s
                    ORDER BY report_date DESC
                    LIMIT 1
                    """,
                    (symbol,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                if isinstance(row, dict):
                    return dict(row)
                cols = [c[0] for c in cur.description]
                return dict(zip(cols, row))
        finally:
            conn.close()
