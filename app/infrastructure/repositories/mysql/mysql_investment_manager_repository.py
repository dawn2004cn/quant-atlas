"""MySQL implementation for InvestmentManagerRepository."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc, func, and_

from ...database.mysql_client import mysql_get_connection
from ...database.models.investment import (
    InvestmentManager as DBManager,
    ManagerNAV as DBNAV,
    ManagerTrade as DBTrade,
    ManagerHoldingsSnap as DBHoldings,
    ManagerPositionState as DBPosition,
)

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManagerRow:
    manager_id: str
    strategy_id: str
    name: str
    bio: str
    cohort: str
    deployed_at: str | None
    active: int
    tagline: str = ""
    specialty: str = ""


class MySQLInvestmentManagerRepository:
    """MySQL implementation of InvestmentManagerRepository."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _to_dict(self, model_obj):
        return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

    def get_manager(self, manager_id: str) -> dict[str, Any] | None:
        if self._session_factory:
            session = self._session_factory()
            try:
                m = session.get(DBManager, manager_id)
                return self._to_dict(m) if m else None
            finally:
                session.close()
        elif self._mysql:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM investment_managers WHERE manager_id = %s", (manager_id,))
                r = cur.fetchone()
                if r:
                    cols = [c[0] for c in cur.description]
                    return dict(zip(cols, r))
                return None
            except Exception:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.get_manager: %s", e)
                cur = conn.cursor()
                cur.execute("SELECT * FROM investment_managers WHERE manager_id = %s", (manager_id,))
                r = cur.fetchone()
                if r:
                    cols = [c[0] for c in cur.description]
                    return dict(zip(cols, r))
                return None
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.get_manager: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_investment_manager_repository.py.get_manager: %s", e)
        return None

    def list_managers(self) -> list[dict[str, Any]]:
        def _rows_to_dicts(cur, rows):
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]

        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBManager).order_by(desc(DBManager.active), DBManager.deployed_at, DBManager.manager_id)
                rows = session.scalars(stmt).all()
                return [self._to_dict(r) for r in rows]
            finally:
                session.close()
        elif self._mysql:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM investment_managers ORDER BY active DESC, deployed_at, manager_id")
                return _rows_to_dicts(cur, cur.fetchall())
            except Exception:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.list_managers: %s", e)
                cur = conn.cursor()
                cur.execute("SELECT * FROM investment_managers ORDER BY active DESC, deployed_at, manager_id")
                return _rows_to_dicts(cur, cur.fetchall())
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.list_managers: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_investment_manager_repository.py.list_managers: %s", e)
        return []

    def upsert_manager(self, row: ManagerRow) -> None:
        if self._session_factory:
            session = self._session_factory()
            try:
                db_m = session.get(DBManager, row.manager_id)
                if not db_m:
                    db_m = DBManager(manager_id=row.manager_id)
                    session.add(db_m)
                db_m.strategy_id = row.strategy_id
                db_m.name = row.name
                db_m.bio = row.bio
                db_m.cohort = row.cohort
                db_m.deployed_at = row.deployed_at
                db_m.active = int(row.active)
                db_m.tagline = row.tagline
                db_m.specialty = row.specialty
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            return
        if self._mysql:
            conn = mysql_get_connection(self._mysql, autocommit=True)
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO investment_managers
                    (manager_id, strategy_id, name, bio, cohort, deployed_at, active, tagline, specialty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    strategy_id = VALUES(strategy_id),
                    name = VALUES(name),
                    bio = VALUES(bio),
                    cohort = VALUES(cohort),
                    tagline = VALUES(tagline),
                    specialty = VALUES(specialty)
                """, (row.manager_id, row.strategy_id, row.name, row.bio, row.cohort, row.deployed_at, int(row.active), row.tagline, row.specialty))
                conn.commit()
            except Exception:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.upsert_manager: %s", e)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO investment_managers
                    (manager_id, strategy_id, name, bio, cohort, deployed_at, active, tagline, specialty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    strategy_id = VALUES(strategy_id),
                    name = VALUES(name),
                    bio = VALUES(bio),
                    cohort = VALUES(cohort),
                    tagline = VALUES(tagline),
                    specialty = VALUES(specialty)
                """, (row.manager_id, row.strategy_id, row.name, row.bio, row.cohort, row.deployed_at, int(row.active), row.tagline, row.specialty))
                conn.commit()
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.upsert_manager: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_investment_manager_repository.py.upsert_manager: %s", e)

    def activate_next_batch(self, *, batch_size: int = 10) -> list[str]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBManager).where(DBManager.active == 0).order_by(DBManager.manager_id).limit(batch_size)
                managers = session.scalars(stmt).all()
                if not managers:
                    return []
                ids = []
                for m in managers:
                    m.active = 1
                    m.deployed_at = now
                    ids.append(m.manager_id)
                session.commit()
                return ids
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return []

    def upsert_nav(self, *, manager_id: str, nav_date: str, equity: float, cash: float, total_fee: float, total_tax: float, note: str = "") -> None:
        nd = nav_date[:10]
        if self._session_factory:
            session = self._session_factory()
            try:
                db_n = session.get(DBNAV, (manager_id, nd))
                if not db_n:
                    db_n = DBNAV(manager_id=manager_id, nav_date=nd)
                    session.add(db_n)
                db_n.equity = float(equity)
                db_n.cash = float(cash)
                db_n.total_fee = float(total_fee)
                db_n.total_tax = float(total_tax)
                db_n.note = str(note or "")
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def get_nav_series(self, manager_id: str, *, limit: int = 420) -> list[dict[str, Any]]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBNAV).where(DBNAV.manager_id == manager_id).order_by(desc(DBNAV.nav_date)).limit(limit)
                rows = session.scalars(stmt).all()
                res = [self._to_dict(r) for r in rows]
                res.reverse()
                return res
            finally:
                session.close()
        return []

    def append_trade(self, payload: dict[str, Any]) -> None:
        if self._session_factory:
            session = self._session_factory()
            try:
                t = DBTrade(
                    manager_id=payload["manager_id"],
                    trade_date=str(payload["trade_date"])[:19],
                    symbol=payload["symbol"],
                    action=payload["action"],
                    reason=payload.get("reason") or "",
                    price=float(payload["price"]),
                    shares=int(payload["shares"]),
                    fee=float(payload.get("fee") or 0.0),
                    tax=float(payload.get("tax") or 0.0)
                )
                session.add(t)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def list_trades(self, manager_id: str, *, limit: int = 400) -> list[dict[str, Any]]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBTrade).where(DBTrade.manager_id == manager_id).order_by(desc(DBTrade.trade_id)).limit(limit)
                rows = session.scalars(stmt).all()
                return [self._to_dict(r) for r in rows]
            finally:
                session.close()
        return []

    def latest_holdings_snap_date_before(self, manager_id: str, snap_date: str) -> str | None:
        d = str(snap_date)[:10]
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(func.max(DBHoldings.snap_date)).where(and_(DBHoldings.manager_id == manager_id, DBHoldings.snap_date < d))
                res = session.execute(stmt).scalar()
                return str(res)[:10] if res else None
            finally:
                session.close()
        return None

    def get_holdings_snap(self, manager_id: str, snap_date: str) -> list[dict[str, Any]]:
        d = str(snap_date)[:10]
        if not d:
            return []
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBHoldings).where(and_(DBHoldings.manager_id == manager_id, DBHoldings.snap_date == d))
                rows = session.execute(stmt).scalars().all()
                return [self._to_dict(r) for r in rows]
            finally:
                session.close()
        elif self._mysql:
            conn = mysql_get_connection(self._mysql, autocommit=True)
            cur = None
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM investment_manager_holdings WHERE manager_id = %s AND snap_date = %s",
                    (manager_id, d)
                )
                rows = cur.fetchall()
                if rows:
                    cols = [c[0] for c in cur.description]
                    return [dict(zip(cols, r)) for r in rows]
                return []
            except Exception:
                return []
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.get_holdings_snap: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_investment_manager_repository.py.get_holdings_snap: %s", e)
        return []

    def upsert_position_state(self, *, manager_id: str, symbol: str, shares: int, avg_cost: float, entry_cost: float, high_px: float, entry_date: str) -> None:
        if self._session_factory:
            session = self._session_factory()
            try:
                p = session.get(DBPosition, (manager_id, symbol))
                if not p:
                    p = DBPosition(manager_id=manager_id, symbol=symbol)
                    session.add(p)
                p.shares = int(shares)
                p.avg_cost = float(avg_cost)
                p.entry_cost = float(entry_cost)
                p.high_px = float(high_px)
                p.entry_date = str(entry_date)[:10]
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def _row_to_dict(self, row, cur) -> dict[str, Any]:
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    def trade_stats_by_manager(self) -> dict[str, dict[str, Any]]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = (
                    select(
                        DBTrade.manager_id,
                        func.count(DBTrade.trade_id).label('trade_count'),
                        func.max(DBTrade.trade_date).label('last_trade_date')
                    )
                    .group_by(DBTrade.manager_id)
                )
                rows = session.execute(stmt).all()
                result = {}
                for row in rows:
                    result[row.manager_id] = {
                        "trade_count": row.trade_count,
                        "last_trade_date": str(row.last_trade_date) if row.last_trade_date else None
                    }
                return result
            finally:
                session.close()
        elif self._mysql:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT manager_id, COUNT(*) as trade_count, MAX(trade_date) as last_trade_date
                    FROM manager_trades
                    GROUP BY manager_id
                """)
                rows = cur.fetchall()
                result = {}
                for row in rows:
                    d = self._row_to_dict(row, cur)
                    result[d["manager_id"]] = {
                        "trade_count": d["trade_count"],
                        "last_trade_date": d["last_trade_date"] if d["last_trade_date"] else None
                    }
                return result
            except Exception:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.trade_stats_by_manager: %s", e)
                cur = conn.cursor()
                cur.execute("""
                    SELECT manager_id, COUNT(*) as trade_count, MAX(trade_date) as last_trade_date
                    FROM manager_trades
                    GROUP BY manager_id
                """)
                rows = cur.fetchall()
                result = {}
                for row in rows:
                    d = self._row_to_dict(row, cur)
                    result[d["manager_id"]] = {
                        "trade_count": d["trade_count"],
                        "last_trade_date": d["last_trade_date"] if d["last_trade_date"] else None
                    }
                return result
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_investment_manager_repository.py.trade_stats_by_manager: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("mysql_investment_manager_repository.py.trade_stats_by_manager: %s", e)
        return {}
