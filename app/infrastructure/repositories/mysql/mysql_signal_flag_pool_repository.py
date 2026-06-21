"""MySQL implementation for SignalFlagPoolRepository."""

import json
from datetime import datetime
from typing import Any
from sqlalchemy import select, delete, insert, update, desc, func, and_

from ...database.mysql_client import mysql_get_connection
from ...database.models.advanced import SignalFlagPool as DBPool


import logging
logger = logging.getLogger(__name__)
class MySQLSignalFlagPoolRepository:
    """MySQL implementation of SignalFlagPoolRepository."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _to_dict(self, model_obj):
        return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

    def list_dates(self, *, limit: int = 120) -> list[str]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBPool.pool_date).group_by(DBPool.pool_date).order_by(desc(DBPool.pool_date)).limit(limit)
                return list(session.scalars(stmt).all())
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT pool_date FROM signal_flag_pool
                GROUP BY pool_date
                ORDER BY pool_date DESC
                LIMIT %s
                """,
                (int(limit),)
            )
            cols = [d[0] for d in cur.description]
            return [str(dict(zip(cols, r))["pool_date"])[:10] for r in cur.fetchall()]
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_signal_flag_pool_repository.py.list_dates: %s", e)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT pool_date FROM signal_flag_pool
                GROUP BY pool_date
                ORDER BY pool_date DESC
                LIMIT %s
                """,
                (int(limit),)
            )
            cols = [d[0] for d in cur.description]
            return [str(dict(zip(cols, r))["pool_date"])[:10] for r in cur.fetchall()]
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_signal_flag_pool_repository.py.list_dates: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_signal_flag_pool_repository.py.list_dates: %s", e)

    def get_pool(self, pool_date: str) -> list[dict[str, Any]]:
        d = (pool_date or "")[:10]
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBPool).where(DBPool.pool_date == d).order_by(desc(DBPool.amount), DBPool.code)
                rows = session.scalars(stmt).all()
                out = []
                for r in rows:
                    item = self._to_dict(r)
                    for k in ("signal_strategies", "signal_strategies_sell", "long_horizon", "mid_horizon", "short_horizon", "extra_snapshot"):
                        if k in item and isinstance(item[k], str):
                            try:
                                item[k] = json.loads(item[k])
                            except json.JSONDecodeError:
                                item[k] = [] if "strategies" in k else {}
                    out.append(item)
                return out
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM signal_flag_pool
                WHERE pool_date = %s
                ORDER BY amount DESC, code ASC
                """,
                (d,)
            )
            out = []
            cols = [d[0] for d in cur.description]
            for r in cur.fetchall():
                item = dict(zip(cols, r))
                for k in ("signal_strategies", "signal_strategies_sell", "long_horizon", "mid_horizon", "short_horizon", "extra_snapshot"):
                    if k in item and isinstance(item[k], str):
                        try:
                            item[k] = json.loads(item[k])
                        except json.JSONDecodeError:
                            item[k] = [] if "strategies" in k else {}
                out.append(item)
            return out
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_signal_flag_pool_repository.py.get_pool: %s", e)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM signal_flag_pool
                WHERE pool_date = %s
                ORDER BY amount DESC, code ASC
                """,
                (d,)
            )
            out = []
            cols = [d[0] for d in cur.description]
            for r in cur.fetchall():
                item = dict(zip(cols, r))
                for k in ("signal_strategies", "signal_strategies_sell", "long_horizon", "mid_horizon", "short_horizon", "extra_snapshot"):
                    if k in item and isinstance(item[k], str):
                        try:
                            item[k] = json.loads(item[k])
                        except json.JSONDecodeError:
                            item[k] = [] if "strategies" in k else {}
                out.append(item)
            return out
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_signal_flag_pool_repository.py.get_pool: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_signal_flag_pool_repository.py.get_pool: %s", e)

    def replace_pool(self, pool_date: str, rows: list[dict[str, Any]]) -> int:
        d = (pool_date or "")[:10]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self._session_factory:
            session = self._session_factory()
            try:
                session.execute(delete(DBPool).where(DBPool.pool_date == d))
                for r in rows:
                    db_p = DBPool(
                        pool_date=d,
                        code=str(r.get("code") or ""),
                        name=str(r.get("name") or ""),
                        price=float(r.get("price") or 0),
                        change_pct=float(r.get("change_pct") or 0),
                        volume=float(r.get("volume") or 0),
                        amount=float(r.get("amount") or 0),
                        turnover=float(r.get("turnover") or 0),
                        source=str(r.get("source") or ""),
                        industry=str(r.get("industry") or ""),
                        pe=float(r.get("pe") or 0),
                        pb=float(r.get("pb") or 0),
                        signal_strategies=json.dumps(r.get("signal_strategies") or [], ensure_ascii=False),
                        signal_strategies_sell=json.dumps(r.get("signal_strategies_sell") or [], ensure_ascii=False),
                        long_horizon=json.dumps(r.get("long_horizon") or {}, ensure_ascii=False),
                        mid_horizon=json.dumps(r.get("mid_horizon") or {}, ensure_ascii=False),
                        short_horizon=json.dumps(r.get("short_horizon") or {}, ensure_ascii=False),
                        safety_score=float(r.get("safety_score") or 0),
                        extra_snapshot=json.dumps(r.get("extra_snapshot") or {}, ensure_ascii=False),
                        created_at=now
                    )
                    session.add(db_p)
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
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute("DELETE FROM signal_flag_pool WHERE pool_date = %s", (d,))
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO signal_flag_pool
                    (pool_date, code, name, price, change_pct, volume, amount, turnover, source, industry, pe, pb,
                    signal_strategies, signal_strategies_sell, long_horizon, mid_horizon, short_horizon, safety_score, extra_snapshot, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        d,
                        str(r.get("code") or ""),
                        str(r.get("name") or ""),
                        float(r.get("price") or 0),
                        float(r.get("change_pct") or 0),
                        float(r.get("volume") or 0),
                        float(r.get("amount") or 0),
                        float(r.get("turnover") or 0),
                        str(r.get("source") or ""),
                        str(r.get("industry") or ""),
                        float(r.get("pe") or 0),
                        float(r.get("pb") or 0),
                        json.dumps(r.get("signal_strategies") or [], ensure_ascii=False),
                        json.dumps(r.get("signal_strategies_sell") or [], ensure_ascii=False),
                        json.dumps(r.get("long_horizon") or {}, ensure_ascii=False),
                        json.dumps(r.get("mid_horizon") or {}, ensure_ascii=False),
                        json.dumps(r.get("short_horizon") or {}, ensure_ascii=False),
                        float(r.get("safety_score") or 0),
                        json.dumps(r.get("extra_snapshot") or {}, ensure_ascii=False),
                        now
                    )
                )
            conn.commit()
            return len(rows)
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                cur = conn.cursor()
                cur.execute("DELETE FROM signal_flag_pool WHERE pool_date = %s", (d,))
                for r in rows:
                    cur.execute(
                        """
                        INSERT INTO signal_flag_pool
                        (pool_date, code, name, price, change_pct, volume, amount, turnover, source, industry, pe, pb,
                        signal_strategies, signal_strategies_sell, long_horizon, mid_horizon, short_horizon, safety_score, extra_snapshot, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            d,
                            str(r.get("code") or ""),
                            str(r.get("name") or ""),
                            float(r.get("price") or 0),
                            float(r.get("change_pct") or 0),
                            float(r.get("volume") or 0),
                            float(r.get("amount") or 0),
                            float(r.get("turnover") or 0),
                            str(r.get("source") or ""),
                            str(r.get("industry") or ""),
                            float(r.get("pe") or 0),
                            float(r.get("pb") or 0),
                            json.dumps(r.get("signal_strategies") or [], ensure_ascii=False),
                            json.dumps(r.get("signal_strategies_sell") or [], ensure_ascii=False),
                            json.dumps(r.get("long_horizon") or {}, ensure_ascii=False),
                            json.dumps(r.get("mid_horizon") or {}, ensure_ascii=False),
                            json.dumps(r.get("short_horizon") or {}, ensure_ascii=False),
                            float(r.get("safety_score") or 0),
                            json.dumps(r.get("extra_snapshot") or {}, ensure_ascii=False),
                            now
                        )
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
                    logger.debug("mysql_signal_flag_pool_repository.py.replace_pool: %s", e)
