from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter
from app.infrastructure.database.mysql_settings import MysqlSettings

logger = logging.getLogger(__name__)

_CHUNK = 8000


class MySQLTdxBaseDataRepository:
    """MySQL writes for TDX base ingest (stocks, blocks, watchlists, finance)."""

    def __init__(self, mysql: MysqlSettings) -> None:
        self._conn_port = MySQLConnectionAdapter(mysql)

    def list_symbols_for_finance_ingest(self, *, limit: int) -> list[str]:
        conn = self._conn_port.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT symbol FROM tdx_watchlist_items ORDER BY symbol LIMIT %s",
                    (limit,),
                )
                symbols = [str(row[0] or "") for row in (cur.fetchall() or []) if row[0]]
                if symbols:
                    return symbols
                cur.execute("SELECT symbol FROM cn_stock_basics ORDER BY symbol LIMIT %s", (limit,))
                return [str(row[0] or "") for row in (cur.fetchall() or []) if row[0]]
        finally:
            conn.close()

    def ingest_base_data(
        self,
        *,
        basics: list[tuple[str, str, str, str, str]],
        block_items: list[tuple[str, str, str, str]],
        ts: str,
        ingest_watchlists: bool,
        watchlists: list[Any],
        watchlist_sync_mode: str,
        watchlist_conflict_strategy: str,
        ingest_finance: bool,
        finance_fetcher: Any,
        finance_max_symbols: int,
        finance_rate_limit_rps: int,
    ) -> dict[str, int]:
        conn = self._conn_port.connect()
        self._conn_port.ensure_schema(conn)
        counts = {
            "stocks_upserted": 0,
            "blocks_upserted": 0,
            "block_items_upserted": 0,
            "watchlists_upserted": 0,
            "watchlist_items_upserted": 0,
            "watchlist_items_added": 0,
            "watchlist_items_skipped": 0,
            "finance_upserted": 0,
            "finance_failed": 0,
        }
        try:
            conn.autocommit(False)
            cur = conn.cursor()

            sql_stock = """
                INSERT INTO cn_stock_basics(symbol, name, market, updated_at, source)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    name=VALUES(name),
                    market=VALUES(market),
                    updated_at=VALUES(updated_at),
                    source=VALUES(source)
            """
            batch: list[tuple[Any, ...]] = []
            for row in basics:
                batch.append(row)
                if len(batch) >= _CHUNK:
                    cur.executemany(sql_stock, batch)
                    counts["stocks_upserted"] += len(batch)
                    batch.clear()
            if batch:
                cur.executemany(sql_stock, batch)
                counts["stocks_upserted"] += len(batch)

            uniq_blocks = sorted({(it[0], it[1]) for it in block_items})
            sql_block = """
                INSERT INTO tdx_blocks(block_kind, block_name, updated_at, source)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    updated_at=VALUES(updated_at),
                    source=VALUES(source)
            """
            block_rows = [(k[0], k[1], ts, "tdx_block_dat") for k in uniq_blocks]
            if block_rows:
                for i in range(0, len(block_rows), _CHUNK):
                    part = block_rows[i : i + _CHUNK]
                    cur.executemany(sql_block, part)
                    counts["blocks_upserted"] += len(part)

            sql_item = """
                INSERT INTO tdx_block_items(block_kind, block_name, symbol, updated_at)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    updated_at=VALUES(updated_at)
            """
            item_batch: list[tuple[Any, ...]] = []
            for row in block_items:
                item_batch.append(row)
                if len(item_batch) >= _CHUNK:
                    cur.executemany(sql_item, item_batch)
                    counts["block_items_upserted"] += len(item_batch)
                    item_batch.clear()
            if item_batch:
                cur.executemany(sql_item, item_batch)
                counts["block_items_upserted"] += len(item_batch)

            if ingest_watchlists and watchlists:
                sql_wl = """
                    INSERT INTO tdx_watchlists(name, source_path, updated_at)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        source_path=VALUES(source_path),
                        updated_at=VALUES(updated_at)
                """
                sql_wli = """
                    INSERT INTO tdx_watchlist_items(watchlist_name, symbol, updated_at)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        updated_at=VALUES(updated_at)
                """
                for wl in watchlists:
                    cur.execute(sql_wl, (wl.name, wl.source_path, ts))
                    counts["watchlists_upserted"] += 1
                    if watchlist_sync_mode == "full":
                        cur.execute(
                            "DELETE FROM tdx_watchlist_items WHERE watchlist_name=%s",
                            (wl.name,),
                        )
                        rows = [(wl.name, s, ts) for s in wl.symbols]
                        for i in range(0, len(rows), _CHUNK):
                            part = rows[i : i + _CHUNK]
                            if part:
                                cur.executemany(sql_wli, part)
                                counts["watchlist_items_upserted"] += len(part)
                    else:
                        cur.execute(
                            "SELECT symbol FROM tdx_watchlist_items WHERE watchlist_name=%s",
                            (wl.name,),
                        )
                        existing = {str(row[0] or "") for row in (cur.fetchall() or [])}
                        rows_to_add = []
                        for s in wl.symbols:
                            if s in existing:
                                if watchlist_conflict_strategy == "overwrite":
                                    cur.execute(sql_wli, (wl.name, s, ts))
                                    counts["watchlist_items_upserted"] += 1
                                elif watchlist_conflict_strategy in ("skip", "merge"):
                                    counts["watchlist_items_skipped"] += 1
                            else:
                                rows_to_add.append((wl.name, s, ts))
                                counts["watchlist_items_added"] += 1
                        for i in range(0, len(rows_to_add), _CHUNK):
                            part = rows_to_add[i : i + _CHUNK]
                            if part:
                                cur.executemany(sql_wli, part)
                                counts["watchlist_items_upserted"] += len(part)

            if ingest_finance and finance_fetcher is not None:
                maxn = max(0, int(finance_max_symbols))
                rps = max(1, int(finance_rate_limit_rps or 1))
                sleep_s = 1.0 / float(rps)
                symbols = self.list_symbols_for_finance_ingest(limit=maxn)
                logger.info("tdx_finance_ingest: symbols=%s rps=%s", len(symbols), rps)
                sql_fin = """
                    INSERT INTO cn_finance_snapshots(
                        symbol, report_date, total_shares, float_shares, eps, bps, net_profit, revenue,
                        fetched_at, source, raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        total_shares=VALUES(total_shares),
                        float_shares=VALUES(float_shares),
                        eps=VALUES(eps),
                        bps=VALUES(bps),
                        net_profit=VALUES(net_profit),
                        revenue=VALUES(revenue),
                        fetched_at=VALUES(fetched_at),
                        source=VALUES(source),
                        raw_json=VALUES(raw_json)
                """
                for sym in symbols:
                    t0 = time.time()
                    try:
                        snap = finance_fetcher(sym)
                        if snap is None or not snap.report_date or snap.report_date == "unknown":
                            counts["finance_failed"] += 1
                        else:
                            raw_json = json.dumps(snap.raw, ensure_ascii=False)
                            cur.execute(
                                sql_fin,
                                (
                                    snap.symbol,
                                    snap.report_date,
                                    snap.total_shares,
                                    snap.float_shares,
                                    snap.eps,
                                    snap.bps,
                                    snap.net_profit,
                                    snap.revenue,
                                    ts,
                                    "tdx_live_finance",
                                    raw_json,
                                ),
                            )
                            counts["finance_upserted"] += 1
                    except Exception as exc:
                        counts["finance_failed"] += 1
                        logger.warning("tdx_finance_ingest failed for %s: %s", sym, exc)
                    dt = time.time() - t0
                    if dt < sleep_s:
                        time.sleep(sleep_s - dt)

            self._conn_port.commit(conn)
        except Exception:
            self._conn_port.rollback(conn)
            raise
        finally:
            conn.close()
        return counts
