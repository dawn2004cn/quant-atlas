"""MySQL implementation for BasicMarketDataRepository."""

import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select, delete, insert, update, desc, func, and_

import pymysql
from pymysql.cursors import DictCursor

from ...database.mysql_client import mysql_get_connection
from ...database.models.market import LonghuDaily as DBLonghu, BasicDataMeta as DBMeta, CNFinancialStash as DBStash
from ...database.models.advanced import YanbaoItem as DBYanbao


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


from app.infrastructure.repositories.factory import register_repo, RepositoryType

import logging
logger = logging.getLogger(__name__)
@register_repo(RepositoryType.MYSQL, "basic_market_data")
class MySQLBasicMarketDataRepository:
    """MySQL implementation of Basic Market Data Repository."""


    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _row_longhu_to_dict(self, r: DBLonghu) -> dict[str, Any]:
        try:
            raw = json.loads(r.raw_json or "{}")
        except (json.JSONDecodeError, TypeError):
            raw = {}
        return {
            "trade_date": r.trade_date, "code": r.code, "name": r.name,
            "reason": r.reason, "detail": raw, "updated_at": r.updated_at
        }

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
                        trade_date=td, code=code, name=(r.get("name") or "")[:64],
                        reason=(r.get("reason") or "")[:512],
                        raw_json=json.dumps(r.get("raw") or r, ensure_ascii=False),
                        updated_at=now
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
                    """
                    INSERT INTO longhu_daily (trade_date, code, name, reason, raw_json, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name=VALUES(name),
                        reason=VALUES(reason),
                        raw_json=VALUES(raw_json),
                        updated_at=VALUES(updated_at)
                    """,
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
                        """
                        INSERT INTO longhu_daily (trade_date, code, name, reason, raw_json, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name=VALUES(name),
                            reason=VALUES(reason),
                            raw_json=VALUES(raw_json),
                            updated_at=VALUES(updated_at)
                        """,
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
                    logger.debug("mysql_basic_market_data_repository.py.replace_longhu_day: %s", e)

    def list_longhu_by_date(self, trade_date: str, *, limit: int = 500) -> list[dict[str, Any]]:
        td = trade_date.strip()[:10]
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBLonghu).where(DBLonghu.trade_date == td).order_by(DBLonghu.code).limit(limit)
                rows = session.scalars(stmt).all()
                return [self._row_longhu_to_dict(r) for r in rows]
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql)
        cur = None
        try:
            cur = conn.cursor(DictCursor)
            cur.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE trade_date=%s
                ORDER BY code
                LIMIT %s
                """,
                (td, int(limit)),
            )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_by_date: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE trade_date=%s
                ORDER BY code
                LIMIT %s
                """,
                (td, int(limit)),
            )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_by_date: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.list_longhu_by_date: %s", e)

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
                """
                INSERT INTO basic_data_meta (`key`, value, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE value=VALUES(value), updated_at=VALUES(updated_at)
                """,
                (key, value, _utc_ts()),
            )
            conn.commit()
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.set_meta: %s", e)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO basic_data_meta (`key`, value, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE value=VALUES(value), updated_at=VALUES(updated_at)
                """,
                (key, value, _utc_ts()),
            )
            conn.commit()
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.set_meta: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.set_meta: %s", e)

    def get_meta(self, key: str) -> str | None:
        if self._session_factory:
            session = self._session_factory()
            try:
                db_m = session.get(DBMeta, key)
                return db_m.value if db_m else None
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        try:
            cur = conn.cursor(DictCursor)
            cur.execute("SELECT value FROM basic_data_meta WHERE key=%s", (key,))
            r = cur.fetchone()
            return str(r["value"]) if r else None
        except Exception:
            conn.ping(reconnect=True)
            cur = conn.cursor(DictCursor)
            cur.execute("SELECT value FROM basic_data_meta WHERE key=%s", (key,))
            r = cur.fetchone()
            return str(r["value"]) if r else None
        finally:
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.get_meta: %s", e)

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
                """
                INSERT INTO cn_financial_stash (code, payload_json, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                """,
                (c, blob, now),
            )
            conn.commit()
        except Exception:
            conn.ping(reconnect=True)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO cn_financial_stash (code, payload_json, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                """,
                (c, blob, now),
            )
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.upsert_financial_stash: %s", e)

    def insert_yanbao_batch(self, category: str, items: list[dict[str, Any]], batch_id: str) -> int:
        now = _utc_ts()
        if self._session_factory:
            session = self._session_factory()
            try:
                for it in items:
                    db_y = DBYanbao(
                        category=category[:64], title=(it.get("title") or "")[:512],
                        stock_code=(it.get("stock_code") or "")[:16] or None,
                        org_name=(it.get("org_name") or "")[:128],
                        pub_date=(it.get("pub_date") or "")[:32],
                        report_url=(it.get("report_url") or "")[:1024],
                        raw_json=json.dumps(it.get("raw") or it, ensure_ascii=False),
                        crawl_batch=batch_id[:32], created_at=now
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
                    """
                    INSERT INTO yanbao_items
                    (category, title, stock_code, org_name, pub_date, report_url, raw_json, crawl_batch, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
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
                    logger.debug("mysql_basic_market_data_repository.py.insert_yanbao_batch: %s", e)
            cur = conn.cursor()
            for it in items:
                cur.execute(
                    """
                    INSERT INTO yanbao_items
                    (category, title, stock_code, org_name, pub_date, report_url, raw_json, crawl_batch, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
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
                    logger.debug("mysql_basic_market_data_repository.py.insert_yanbao_batch: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.insert_yanbao_batch: %s", e)

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

    def count_longhu_rows(self) -> int:
        if self._session_factory:
            session = self._session_factory()
            try:
                return int(session.query(func.count(DBLonghu.id)).scalar() or 0)
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor(DictCursor)
            cur.execute("SELECT COUNT(1) AS n FROM longhu_daily")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.count_longhu_rows: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute("SELECT COUNT(1) AS n FROM longhu_daily")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.count_longhu_rows: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.count_longhu_rows: %s", e)

    def latest_longhu_trade_date(self) -> str | None:
        if self._session_factory:
            session = self._session_factory()
            try:
                row = session.execute(select(func.max(DBLonghu.trade_date))).scalar()
                return str(row)[:10] if row else None
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAX(trade_date) AS d FROM longhu_daily")
            row = cur.fetchone()
            return str(row[0])[:10] if row and row[0] else None
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.latest_longhu_trade_date: %s", e)
            cur = conn.cursor()
            cur.execute("SELECT MAX(trade_date) AS d FROM longhu_daily")
            row = cur.fetchone()
            return str(row[0])[:10] if row and row[0] else None
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.latest_longhu_trade_date: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.latest_longhu_trade_date: %s", e)

    def list_longhu_latest_dates(self, limit: int = 20) -> list[str]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = (
                    select(DBLonghu.trade_date)
                    .distinct()
                    .order_by(desc(DBLonghu.trade_date))
                    .limit(int(limit))
                )
                rows = session.scalars(stmt).all()
                return [str(row)[:10] for row in rows]
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT trade_date
                FROM longhu_daily
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()
            return [str(row[0])[:10] for row in rows]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_latest_dates: %s", e)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT trade_date
                FROM longhu_daily
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()
            return [str(row[0])[:10] for row in rows]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_latest_dates: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.list_longhu_latest_dates: %s", e)

    def list_longhu_for_code(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        c = str(code or "").strip()[-6:].zfill(6)
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = (
                    select(DBLonghu)
                    .where(DBLonghu.code == c)
                    .order_by(desc(DBLonghu.trade_date))
                    .limit(int(limit))
                )
                rows = session.scalars(stmt).all()
                return [self._row_longhu_to_dict(r) for r in rows]
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor(DictCursor)
            cur.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE code=%s
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (c, int(limit)),
            )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_for_code: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE code=%s
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (c, int(limit)),
            )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_longhu_for_code: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.list_longhu_for_code: %s", e)

    def list_yanbao(self, *, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 1000))
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBYanbao)
                if category:
                    stmt = stmt.where(DBYanbao.category == category)
                stmt = stmt.order_by(desc(DBYanbao.id)).limit(lim)
                rows = session.scalars(stmt).all()
                out: list[dict[str, Any]] = []
                for r in rows:
                    try:
                        raw = json.loads(str(r.raw_json or "{}"))
                    except Exception:
                        raw = {}
                    out.append(
                        {
                            "id": int(r.id),
                            "category": str(r.category),
                            "title": str(r.title or ""),
                            "stock_code": str(r.stock_code or ""),
                            "org_name": str(r.org_name or ""),
                            "pub_date": str(r.pub_date or ""),
                            "report_url": str(r.report_url or ""),
                            "raw": raw,
                            "crawl_batch": str(r.crawl_batch or ""),
                            "created_at": str(r.created_at or ""),
                        }
                    )
                return out
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            if category:
                cur.execute(
                    """
                    SELECT * FROM yanbao_items
                    WHERE category=%s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (category, lim),
                )
            else:
                cur.execute(
                    "SELECT * FROM yanbao_items ORDER BY id DESC LIMIT %s",
                    (lim,),
                )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "id": int(r["id"]),
                        "category": str(r["category"] or ""),
                        "title": str(r["title"] or ""),
                        "stock_code": str(r["stock_code"] or ""),
                        "org_name": str(r["org_name"] or ""),
                        "pub_date": str(r["pub_date"] or ""),
                        "report_url": str(r["report_url"] or ""),
                        "raw": raw,
                        "crawl_batch": str(r["crawl_batch"] or ""),
                        "created_at": str(r["created_at"] or ""),
                    }
                )
            return out
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_yanbao: %s", e)
            cur = conn.cursor(DictCursor)
            if category:
                cur.execute(
                    """
                    SELECT * FROM yanbao_items
                    WHERE category=%s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (category, lim),
                )
            else:
                cur.execute(
                    "SELECT * FROM yanbao_items ORDER BY id DESC LIMIT %s",
                    (lim,),
                )
            rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "id": int(r["id"]),
                        "category": str(r["category"] or ""),
                        "title": str(r["title"] or ""),
                        "stock_code": str(r["stock_code"] or ""),
                        "org_name": str(r["org_name"] or ""),
                        "pub_date": str(r["pub_date"] or ""),
                        "report_url": str(r["report_url"] or ""),
                        "raw": raw,
                        "crawl_batch": str(r["crawl_batch"] or ""),
                        "created_at": str(r["created_at"] or ""),
                    }
                )
            return out
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.list_yanbao: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.list_yanbao: %s", e)

    def count_financial_stash_rows(self) -> int:
        if self._session_factory:
            session = self._session_factory()
            try:
                return int(session.query(func.count(DBStash.code)).scalar() or 0)
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS n FROM cn_financial_stash")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.count_financial_stash_rows: %s", e)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS n FROM cn_financial_stash")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_basic_market_data_repository.py.count_financial_stash_rows: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_basic_market_data_repository.py.count_financial_stash_rows: %s", e)
