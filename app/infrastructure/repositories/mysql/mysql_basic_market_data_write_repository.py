"""Write-only repository for basic market data (MySQL).

Extracted from mysql_basic_market_data_repository.py — contains all
write / mutate methods (longhu, financial stash, yanbao, meta).
"""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete

from ...database.models.advanced import YanbaoItem as DBYanbao
from ...database.models.market import BasicDataMeta as DBMeta
from ...database.models.market import CNFinancialStash as DBStash
from ...database.models.market import LonghuDaily as DBLonghu
from ...database.mysql_client import mysql_get_connection

import logging

logger = logging.getLogger(__name__)


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class MySQLBasicMarketDataWriteRepository:
    """Write-side implementation for basic market data (MySQL)."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Longhu — write methods
    # ------------------------------------------------------------------

    def replace_longhu_day(self, trade_date: str, rows: list[dict[str, Any]]) -> int:
        td = trade_date.strip()[:10]
        now = _utc_ts()
        if self._session_factory:
            session = self._session_factory()
            try:
                session.execute(delete(DBLonghu).where(DBLonghu.trade_date == td))
                for r in rows:
                    code = str(r.get("code") or "").strip()[-6:].zfill(6) if r.get("code") else ""
                    if not code or not code.isdigit():
                        continue
                    db_l = DBLonghu(
                        trade_date=td,
                        code=code,
                        name=(r.get("name") or "")[:64],
                        reason=(r.get("reason") or "")[:512],
                        raw_json=json.dumps(r.get("raw") or r, ensure_ascii=False),
                        updated_at=now,
                    )
                    session.add(db_l)
                session.commit()
                return len(rows)
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._session_factory.remove()

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=True)
            cur = conn.cursor()
            cur.execute("DELETE FROM longhu_daily WHERE trade_date=%s", (td,))
            for r in rows:
                code = str(r.get("code") or "").strip()[-6:].zfill(6)
                if not code.isdigit():
                    continue
                cur.execute(
                    "INSERT INTO longhu_daily (trade_date, code, name, reason, raw_json, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE "
                    "name=VALUES(name), reason=VALUES(reason), "
                    "raw_json=VALUES(raw_json), updated_at=VALUES(updated_at)",
                    (
                        td,
                        code,
                        str(r.get("name") or "")[:64],
                        str(r.get("reason") or "")[:512],
                        json.dumps(r.get("raw") or r, ensure_ascii=False),
                        now,
                    ),
                )
            conn.commit()
            return len(rows)
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                cur = conn.cursor()
                cur.execute("DELETE FROM longhu_daily WHERE trade_date=%s", (td,))
                for r in rows:
                    code = str(r.get("code") or "").strip()[-6:].zfill(6)
                    if not code.isdigit():
                        continue
                    cur.execute(
                        "INSERT INTO longhu_daily (trade_date, code, name, reason, raw_json, updated_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON DUPLICATE KEY UPDATE "
                        "name=VALUES(name), reason=VALUES(reason), "
                        "raw_json=VALUES(raw_json), updated_at=VALUES(updated_at)",
                        (
                            td,
                            code,
                            str(r.get("name") or "")[:64],
                            str(r.get("reason") or "")[:512],
                            json.dumps(r.get("raw") or r, ensure_ascii=False),
                            now,
                        ),
                    )
                conn.commit()
                return len(rows)
            return 0
        finally:
            if cur:
                cur.close()
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("replace_longhu_day: %s", e)

    def upsert_longhu_rows(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        grouped: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            td = str(r.get("trade_date") or "")[:10]
            if not td:
                continue
            grouped.setdefault(td, []).append(r)
        total = 0
        for td, sub in grouped.items():
            total += self.replace_longhu_day(td, sub)
        return total

    # ------------------------------------------------------------------
    # Financial stash — write
    # ------------------------------------------------------------------

    def upsert_financial_stash(self, code: str, payload: dict[str, Any]) -> None:
        c = str(code).strip()[-6:].zfill(6)
        if len(c) != 6 or not c.isdigit():
            return
        now = _utc_ts()
        blob = json.dumps(payload, ensure_ascii=False)
        if self._session_factory:
            session = self._session_factory()
            try:
                db_s = session.get(DBStash, c)
                if not db_s:
                    db_s = DBStash(code=c)
                    session.add(db_s)
                db_s.payload_json = blob
                db_s.updated_at = now
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._session_factory.remove()
            return

        conn = mysql_get_connection(self._mysql, autocommit=True)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO cn_financial_stash (code, payload_json, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)",
                (c, blob, now),
            )
            conn.commit()
        except Exception:
            conn.ping(reconnect=True)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO cn_financial_stash (code, payload_json, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)",
                (c, blob, now),
            )
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception as e:
                logger.debug("upsert_financial_stash: %s", e)

    # ------------------------------------------------------------------
    # Yanbao — write
    # ------------------------------------------------------------------

    def insert_yanbao_batch(self, category: str, items: list[dict[str, Any]], batch_id: str) -> int:
        now = _utc_ts()
        if self._session_factory:
            session = self._session_factory()
            try:
                for it in items:
                    db_y = DBYanbao(
                        category=category[:64],
                        title=(it.get("title") or "")[:512],
                        stock_code=(it.get("stock_code") or "")[:16] or None,
                        org_name=(it.get("org_name") or "")[:128],
                        pub_date=(it.get("pub_date") or "")[:32],
                        report_url=(it.get("report_url") or "")[:1024],
                        raw_json=json.dumps(it.get("raw") or it, ensure_ascii=False),
                        crawl_batch=batch_id[:32],
                        created_at=now,
                    )
                    session.add(db_y)
                session.commit()
                return len(items)
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            for it in items:
                cur.execute(
                    "INSERT INTO yanbao_items "
                    "(category, title, stock_code, org_name, pub_date, report_url, raw_json, crawl_batch, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        category[:64],
                        str(it.get("title") or "")[:512],
                        (str(it.get("stock_code") or "")[:16] or None),
                        str(it.get("org_name") or "")[:128],
                        str(it.get("pub_date") or "")[:32],
                        str(it.get("report_url") or "")[:1024],
                        json.dumps(it.get("raw") or it, ensure_ascii=False),
                        batch_id[:32],
                        now,
                    ),
                )
            conn.commit()
            return len(items)
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("insert_yanbao_batch: %s", e)
            cur = conn.cursor()
            for it in items:
                cur.execute(
                    "INSERT INTO yanbao_items "
                    "(category, title, stock_code, org_name, pub_date, report_url, raw_json, crawl_batch, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        category[:64],
                        str(it.get("title") or "")[:512],
                        (str(it.get("stock_code") or "")[:16] or None),
                        str(it.get("org_name") or "")[:128],
                        str(it.get("pub_date") or "")[:32],
                        str(it.get("report_url") or "")[:1024],
                        json.dumps(it.get("raw") or it, ensure_ascii=False),
                        batch_id[:32],
                        now,
                    ),
                )
            conn.commit()
            return len(items)
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("insert_yanbao_batch: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("insert_yanbao_batch: %s", e)

    # ------------------------------------------------------------------
    # Meta — write
    # ------------------------------------------------------------------

    def set_meta(self, key: str, value: str) -> None:
        if self._session_factory:
            session = self._session_factory()
            try:
                db_m = session.get(DBMeta, key)
                if not db_m:
                    db_m = DBMeta(key=key)
                    session.add(db_m)
                db_m.value = value
                db_m.updated_at = _utc_ts()
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._session_factory.remove()
            return

        conn = mysql_get_connection(self._mysql)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO basic_data_meta (`key`, value, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE value=VALUES(value), updated_at=VALUES(updated_at)",
                (key, value, _utc_ts()),
            )
            conn.commit()
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("set_meta: %s", e)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO basic_data_meta (`key`, value, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE value=VALUES(value), updated_at=VALUES(updated_at)",
                (key, value, _utc_ts()),
            )
            conn.commit()
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("set_meta: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("set_meta: %s", e)