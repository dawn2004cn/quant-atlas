"""ORM Facade - 5 高频 Repository 示范迁移

展示如何用 SQLAlchemy ORM 替代原生 SQL，提升代码可维护性。

迁移优先级:
1. MySQLUserRepository (高频 CRUD)
2. MySQLWatchlistRepository (高频读写)
3. MySQLStockGroupRepository (高频分组操作)
4. MySQLBasicMarketDataRepository (高频行情查询)
5. MySQLSignalObservationRepository (高频信号记录)
"""
from __future__ import annotations
from typing import Any, Optional, List
from datetime import datetime
from sqlalchemy import select, func, and_, desc, update, delete
from sqlalchemy.orm import joinedload

from app.core.logger import get_logger
from app.infrastructure.database.orm import bootstrap_schema
from app.infrastructure.database.models.auth import User, Role
from app.infrastructure.database.models.market import (
    Watchlist, StockGroup, StockGroupItem, StockHistory
)

logger = get_logger(__name__)


class ORMUserFacade:
    """MySQLUserRepository ORM 迁移示范"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def list_users(self) -> List[dict]:
        """替代 list_users() - 使用 ORM eager load"""
        session = self._session_factory()
        try:
            stmt = (
                select(User)
                .options(joinedload(User.role_rel))
                .limit(100)
            )
            users = session.scalars(stmt).all()
            return [
                {
                    "user_id": u.id,
                    "username": u.username,
                    "role": u.role or (u.role_rel.code if u.role_rel else ""),
                    "password_hash": u.password_hash,
                    "avatar_url": u.avatar_url,
                }
                for u in users
            ]
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_username(self, username: str) -> Optional[dict]:
        """替代 get_by_username()"""
        session = self._session_factory()
        try:
            u = session.scalars(
                select(User)
                .options(joinedload(User.role_rel))
                .where(User.username == username)
            ).first()
            if not u:
                return None
            return {
                "user_id": u.id,
                "username": u.username,
                "role": u.role or (u.role_rel.code if u.role_rel else ""),
                "password_hash": u.password_hash,
                "avatar_url": u.avatar_url,
            }
        finally:
            session.close()
            self._session_factory.remove()

    def create_user(self, username: str, password_hash: str, role_code: str) -> bool:
        """替代 create_user() - 使用 ORM"""
        session = self._session_factory()
        try:
            role = session.scalars(
                select(Role).where(Role.code == role_code)
            ).first()
            if not role:
                return False
            new_user = User(
                username=username,
                password_hash=password_hash,
                role=role_code,
                role_id=role.id,
            )
            session.add(new_user)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()


class ORMWatchlistFacade:
    """MySQLWatchlistRepository ORM 迁移示范"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def list_symbols(self, user_id: int = 1) -> List[str]:
        """替代 list_symbols() - 使用 ORM where"""
        session = self._session_factory()
        try:
            stmt = select(Watchlist.symbol).where(
                Watchlist.user_id == user_id
            ).order_by(Watchlist.symbol)
            return [str(s) for s in session.scalars(stmt).all()]
        finally:
            session.close()
            self._session_factory.remove()

    def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        """替代 add_symbol() - 使用 ORM upsert"""
        session = self._session_factory()
        try:
            existing = session.scalars(
                select(Watchlist).where(
                    Watchlist.symbol == symbol,
                    Watchlist.user_id == user_id
                )
            ).first()
            if existing:
                return True
            session.add(Watchlist(symbol=symbol, user_id=user_id))
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        """替代 remove_symbol() - 使用 ORM delete"""
        session = self._session_factory()
        try:
            stmt = delete(Watchlist).where(
                Watchlist.symbol == symbol,
                Watchlist.user_id == user_id
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()


class ORMStockGroupFacade:
    """MySQLStockGroupRepository ORM 迁移示范"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def list_groups(self, user_id: int = 1) -> List[dict]:
        """替代 list_groups() - 使用 ORM order_by"""
        session = self._session_factory()
        try:
            stmt = (
                select(StockGroup)
                .where(StockGroup.user_id == user_id)
                .order_by(desc(StockGroup.is_default), StockGroup.id)
            )
            groups = session.scalars(stmt).all()
            return [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "is_default": bool(g.is_default),
                    "color": getattr(g, 'color', '#3B82F6')
                }
                for g in groups
            ]
        finally:
            session.close()
            self._session_factory.remove()

    def add_symbol_to_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        """替代 add_symbol_to_group() - 使用 ORM merge"""
        session = self._session_factory()
        try:
            g = session.get(StockGroup, group_id)
            if not g or g.user_id != user_id:
                return False
            from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
            normalized = SymbolNormalizer.to_db_code(str(symbol))
            existing = session.scalars(
                select(StockGroupItem).where(
                    and_(
                        StockGroupItem.group_id == group_id,
                        StockGroupItem.symbol == normalized,
                        StockGroupItem.user_id == user_id,
                        StockGroupItem.is_removed == 0
                    )
                )
            ).first()
            if existing:
                existing.is_removed = 0
                existing.added_at = datetime.now()
            else:
                session.add(StockGroupItem(
                    group_id=group_id,
                    symbol=normalized,
                    user_id=user_id,
                    added_at=datetime.now()
                ))
            default_group = session.scalars(
                select(StockGroup).where(
                    and_(
                        StockGroup.is_default == 1,
                        StockGroup.user_id == user_id
                    )
                )
            ).first()
            if default_group and default_group.id != group_id:
                def_existing = session.scalars(
                    select(StockGroupItem).where(
                        and_(
                            StockGroupItem.group_id == default_group.id,
                            StockGroupItem.symbol == normalized,
                            StockGroupItem.user_id == user_id
                        )
                    )
                ).first()
                if def_existing:
                    def_existing.is_removed = 0
                else:
                    session.add(StockGroupItem(
                        group_id=default_group.id,
                        symbol=normalized,
                        user_id=user_id,
                        added_at=datetime.now()
                    ))
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()


class ORMMarketDataFacade:
    """MySQLBasicMarketDataRepository ORM 迁移示范"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get_historical_bars(
        self,
        market: str,
        symbol: str,
        start_date: str,
        end_date: str,
        limit: int = 1000
    ) -> List[dict]:
        """替代 get_history() - 使用 ORM filter + limit"""
        session = self._session_factory()
        try:
            stmt = (
                select(StockHistory)
                .where(
                    and_(
                        StockHistory.market == market,
                        StockHistory.symbol == symbol,
                        StockHistory.date >= start_date,
                        StockHistory.date <= end_date
                    )
                )
                .order_by(StockHistory.date)
                .limit(limit)
            )
            bars = session.scalars(stmt).all()
            return [
                {
                    "date": b.date,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": float(b.volume) if b.volume else 0,
                }
                for b in bars
            ]
        finally:
            session.close()
            self._session_factory.remove()


class ORMSignalObservationFacade:
    """MySQLSignalObservationRepository ORM ????

    ??: signal_observations ??? ORM ????
    ??? text() SQL ? ORM ??????
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def create_observation(self, observation_data: dict) -> bool:
        """?? create() - ORM ????"""
        session = self._session_factory()
        try:
            from sqlalchemy import text
            cols = ', '.join(f':{k}' for k in observation_data.keys())
            names = ', '.join(f'"{k}"' for k in observation_data.keys())
            session.execute(
                text(f'INSERT INTO signal_observations ({names}) VALUES ({cols})'),
                observation_data
            )
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def list_recent_signals(
        self,
        user_id: int = 1,
        limit: int = 100
    ) -> List[dict]:
        """?? list_recent() - ORM ????"""
        session = self._session_factory()
        try:
            from sqlalchemy import text
            result = session.execute(
                text('SELECT * FROM signal_observations WHERE user_id = :uid ORDER BY created_at DESC LIMIT :lim'),
                {'uid': user_id, 'lim': limit}
            )
            return [dict(row._mapping) for row in result.fetchall()]
        finally:
            session.close()
            self._session_factory.remove()