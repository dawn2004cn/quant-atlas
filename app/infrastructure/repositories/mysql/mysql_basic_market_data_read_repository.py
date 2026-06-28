"""Read-only repository for basic market data (MySQL).

Extracted from mysql_basic_market_data_repository.py — contains all
query / read-side methods (longhu, yanbao, meta, financial stash).
"""

import json
from datetime import datetime, timezone
from typing import Any

import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy import desc, func, select

from ...database.models.advanced import YanbaoItem as DBYanbao
from ...database.models.market import BasicDataMeta as DBMeta
from ...database.models.market import CNFinancialStash as DBStash
from ...database.models.market import LonghuDaily as DBLonghu
from ...database.mysql_client import mysql_get_connection

import logging

logger = logging.getLogger(__name__)


class MySQLBasicMarketDataReadRepository:
    """Read-side implementation for basic market data (MySQL)."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_longhu_to_dict(r: DBLonghu) -> dict[str, Any]:
        try:
            raw = json.loads(r.raw_json or "{}")
        except (json.JSONDecodeError, TypeError):
            raw = {}
        return {
            "trade_date": r.trade_date,
            "code": r.code,
            "name": r.name,
            "reason": r.reason,
            "detail": raw,
            "updated_at": r.updated_at,
        }

    @staticmethod
    def _build_longhu_dict_from_raw(r: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = json.loads(str(r.get("raw_json") or "{}"))
        except Exception:
            raw = {}
        return {
            "trade_date": str(r.get("trade_date") or ""),
            "code": str(r.get("code") or ""),
            "name": str(r.get("name") or ""),
            "reason": str(r.get("reason") or ""),
            "detail": raw,
            "updated_at": str(r.get("updated_at") or ""),
        }

    @staticmethod
    def _build_yanbao_dict(r: DBYanbao) -> dict[str, Any]:
        try:
            raw = json.loads(str(r.raw_json or "{}"))
        except Exception:
            raw = {}
        return {
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

    @staticmethod
    def _build_yanbao_dict_from_raw(r: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = json.loads(str(r.get("raw_json") or "{}"))
        except Exception:
            raw = {}
        return {
            "id": int(r.get("id") or 0),
            "category": str(r.get("category") or ""),
            "title": str(r.get("title") or ""),
            "stock_code": str(r.get("stock_code") or ""),
            "org_name": str(r.get("org_name") or ""),
            "pub_date": str(r.get("pub_date") or ""),
            "report_url": str(r.get("report_url") or ""),
            "raw": raw,
            "crawl_batch": str(r.get("crawl_batch") or ""),
            "created_at": str(r.get("created_at") or ""),
        }

    # ------------------------------------------------------------------
    # Longhu — read methods
    # ------------------------------------------------------------------

    def list_longhu_by_date(self, trade_date: str, *, limit: int = 500) -> list[dict[str, Any]]:
        td = trade_date.strip()[:10]
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = (
                    select(DBLonghu)
                    .where(DBLonghu.trade_date == td)
                    .order_by(DBLonghu.code)
                    .limit(limit)
                )
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
                "SELECT trade_date, code, name, reason, raw_json, updated_at "
                "FROM longhu_daily WHERE trade_date=%s ORDER BY code LIMIT %s",
                (td, int(limit)),
            )
            return [self._build_longhu_dict_from_raw(r) for r in cur.fetchall()]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_by_date: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute(
                "SELECT trade_date, code, name, reason, raw_json, updated_at "
                "FROM longhu_daily WHERE trade_date=%s ORDER BY code LIMIT %s",
                (td, int(limit)),
            )
            return [self._build_longhu_dict_from_raw(r) for r in cur.fetchall()]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_by_date: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("list_longhu_by_date: %s", e)

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
                "SELECT DISTINCT trade_date FROM longhu_daily ORDER BY trade_date DESC LIMIT %s",
                (int(limit),),
            )
            return [str(row[0])[:10] for row in cur.fetchall()]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_latest_dates: %s", e)
            cur = conn.cursor()
            cur.execute(
                "SELECT DISTINCT trade_date FROM longhu_daily ORDER BY trade_date DESC LIMIT %s",
                (int(limit),),
            )
            return [str(row[0])[:10] for row in cur.fetchall()]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_latest_dates: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("list_longhu_latest_dates: %s", e)

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
                "SELECT trade_date, code, name, reason, raw_json, updated_at "
                "FROM longhu_daily WHERE code=%s ORDER BY trade_date DESC LIMIT %s",
                (c, int(limit)),
            )
            return [self._build_longhu_dict_from_raw(r) for r in cur.fetchall()]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_for_code: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute(
                "SELECT trade_date, code, name, reason, raw_json, updated_at "
                "FROM longhu_daily WHERE code=%s ORDER BY trade_date DESC LIMIT %s",
                (c, int(limit)),
            )
            return [self._build_longhu_dict_from_raw(r) for r in cur.fetchall()]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_longhu_for_code: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("list_longhu_for_code: %s", e)

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
                    logger.debug("count_longhu_rows: %s", e)
            cur = conn.cursor(DictCursor)
            cur.execute("SELECT COUNT(1) AS n FROM longhu_daily")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("count_longhu_rows: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("count_longhu_rows: %s", e)

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
                    logger.debug("latest_longhu_trade_date: %s", e)
            cur = conn.cursor()
            cur.execute("SELECT MAX(trade_date) AS d FROM longhu_daily")
            row = cur.fetchone()
            return str(row[0])[:10] if row and row[0] else None
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("latest_longhu_trade_date: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("latest_longhu_trade_date: %s", e)

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
                    logger.debug("count_financial_stash_rows: %s", e)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS n FROM cn_financial_stash")
            row = cur.fetchone()
            return int(row["n"] if row else 0)
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("count_financial_stash_rows: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("count_financial_stash_rows: %s", e)

    # ------------------------------------------------------------------
    # Yanbao — read methods
    # ------------------------------------------------------------------

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
                return [self._build_yanbao_dict(r) for r in rows]
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            if category:
                cur.execute(
                    "SELECT * FROM yanbao_items WHERE category=%s ORDER BY id DESC LIMIT %s",
                    (category, lim),
                )
            else:
                cur.execute("SELECT * FROM yanbao_items ORDER BY id DESC LIMIT %s", (lim,))
            return [self._build_yanbao_dict_from_raw(r) for r in cur.fetchall()]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_yanbao: %s", e)
            cur = conn.cursor(DictCursor)
            if category:
                cur.execute(
                    "SELECT * FROM yanbao_items WHERE category=%s ORDER BY id DESC LIMIT %s",
                    (category, lim),
                )
            else:
                cur.execute("SELECT * FROM yanbao_items ORDER BY id DESC LIMIT %s", (lim,))
            return [self._build_yanbao_dict_from_raw(r) for r in cur.fetchall()]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("list_yanbao: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("list_yanbao: %s", e)

    # ------------------------------------------------------------------
    # Meta — read side
    # ------------------------------------------------------------------

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
                logger.debug("get_meta: %s", e)
