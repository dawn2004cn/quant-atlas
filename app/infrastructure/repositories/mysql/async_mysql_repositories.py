from __future__ import annotations

"""Asynchronous repository implementations for Phase 41 migration.

This module provides async versions of MySQL repositories, replacing
blocking pymysql calls with SQLAlchemy AsyncSession + asyncmy.

Key benefits:
- Non-blocking I/O: No thread blocking during DB operations
- Higher concurrency: Handle more simultaneous requests
- Better resource utilization: Reduced thread pool exhaustion
"""


import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.query_limits import MAX_WATCHLIST_SYMBOLS
from app.domain.entities import UserAccount
from app.infrastructure.database.models.advanced import SignalFlagPool
from app.infrastructure.database.models.auth import User
from app.infrastructure.database.models.investment import (
    InvestmentManager,
    ManagerHoldingsSnap,
    ManagerNAV,
    ManagerTrade,
)
from app.infrastructure.database.models.market import StockGroup, StockGroupItem, Watchlist
from app.infrastructure.database.models.trading import FTOrder, FTTrade
from app.infrastructure.repositories.common.user_mapper import user_row_to_account


class AsyncRepositoryBase:
    """Base class for all async repositories."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory


class AsyncMySQLUserRepository(AsyncRepositoryBase):
    """Async implementation of UserRepository."""

    @staticmethod
    def _map_user(u: User) -> UserAccount:
        return user_row_to_account(
            user_id=u.id,
            username=u.username,
            role=u.role,
            password_hash=u.password_hash,
            avatar_url=u.avatar_url,
        )

    async def list_users(self) -> list[UserAccount]:
        from app.core.query_limits import MAX_USERS

        async with self._session_factory() as session:
            result = await session.execute(select(User).limit(MAX_USERS))
            users = result.scalars().all()
            return [self._map_user(u) for u in users]

    async def get_by_username(self, username: str) -> UserAccount | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            u = result.scalars().first()
            if not u:
                return None
            return self._map_user(u)

    async def get_by_id(self, user_id: str) -> UserAccount | None:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        async with self._session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == uid)
            )
            u = result.scalars().first()
            if not u:
                return None
            return self._map_user(u)

    async def create(self, user: UserAccount) -> str:
        async with self._session_factory() as session:
            db_user = User(
                username=user.username,
                password_hash=user.password_hash,
                role=user.role,
                avatar_url=user.avatar_url or None,
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
            return str(db_user.id)

    async def update(self, user_id: str, data: dict[str, Any]) -> bool:
        async with self._session_factory() as session:
            stmt = update(User).where(User.id == user_id).values(**data)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete(self, user_id: str) -> bool:
        async with self._session_factory() as session:
            stmt = delete(User).where(User.id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def list_all(self, limit: int = 100) -> list[UserAccount]:
        async with self._session_factory() as session:
            result = await session.execute(select(User).limit(max(1, int(limit))))
            users = result.scalars().all()
            return [self._map_user(u) for u in users]


class AsyncMySQLWatchlistRepository(AsyncRepositoryBase):
    """Async implementation of WatchlistRepository.

    Migration from sync pymysql:
    - list_symbols() -> async list_symbols()
    - add_symbol() -> async add_symbol()
    - remove_symbol() -> async remove_symbol()
    - save_symbols() -> async save_symbols()
    """

    async def list_symbols(self, user_id: int = 1) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Watchlist.symbol)
                .where(Watchlist.user_id == user_id)
                .limit(MAX_WATCHLIST_SYMBOLS)
            )
            return [row[0] for row in result.all()]

    async def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        async with self._session_factory() as session:
            try:
                existing = await session.execute(
                    select(Watchlist).where(
                        Watchlist.symbol == normalized,
                        Watchlist.user_id == user_id,
                    )
                )
                if existing.scalars().first():
                    return True

                watchlist_item = Watchlist(symbol=normalized, user_id=user_id)
                session.add(watchlist_item)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False

    async def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        async with self._session_factory() as session:
            stmt = delete(Watchlist).where(
                Watchlist.symbol == normalized,
                Watchlist.user_id == user_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def save_symbols(self, user_id: int, symbols: list[str]) -> None:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        async with self._session_factory() as session:
            await session.execute(
                delete(Watchlist).where(Watchlist.user_id == user_id)
            )
            for symbol in symbols:
                normalized = SymbolNormalizer.to_db_code(symbol)
                session.add(Watchlist(symbol=normalized, user_id=user_id))
            await session.commit()

    async def get_by_user(self, user_id: str) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Watchlist)
                .where(Watchlist.user_id == int(user_id))
                .limit(MAX_WATCHLIST_SYMBOLS)
            )
            return [{"symbol": w.symbol, "user_id": w.user_id} for w in result.scalars().all()]

    async def add_stock(
        self, user_id: str, stock_code: str, watchlist_name: str = "default"
    ) -> dict:
        success = await self.add_symbol(stock_code, int(user_id))
        return {"success": success, "stock_code": stock_code}

    async def remove_stock(
        self, user_id: str, stock_code: str, watchlist_name: str = "default"
    ) -> bool:
        return await self.remove_symbol(stock_code, int(user_id))


class AsyncMySQLStockGroupRepository(AsyncRepositoryBase):
    """Async implementation of StockGroupRepository.

    Migration from sync pymysql:
    - list_groups() -> async list_groups()
    - create_group() -> async create_group()
    - update_group() -> async update_group()
    - delete_group() -> async delete_group()
    - list_group_symbols() -> async list_group_symbols()
    - add_symbol_to_group() -> async add_symbol_to_group()
    - remove_symbol_from_group() -> async remove_symbol_from_group()
    """

    async def list_groups(self, user_id: int = 1) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockGroup).where(StockGroup.user_id == user_id)
            )
            return [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "is_default": g.is_default,
                }
                for g in result.scalars().all()
            ]

    async def create_group(
        self, name: str, description: str = "", color: str = "", user_id: int = 1
    ) -> dict | None:
        async with self._session_factory() as session:
            try:
                group = StockGroup(
                    name=name,
                    description=description,
                    user_id=user_id,
                )
                session.add(group)
                await session.commit()
                return {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                }
            except Exception:
                await session.rollback()
                return None

    async def update_group(
        self,
        group_id: int,
        name: str,
        description: str = "",
        color: str = "",
        user_id: int = 1,
    ) -> bool:
        async with self._session_factory() as session:
            stmt = (
                update(StockGroup)
                .where(StockGroup.id == group_id, StockGroup.user_id == user_id)
                .values(name=name, description=description)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        async with self._session_factory() as session:
            stmt = delete(StockGroup).where(
                StockGroup.id == group_id, StockGroup.user_id == user_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockGroupItem.symbol).where(
                    StockGroupItem.group_id == group_id,
                    StockGroupItem.user_id == user_id,
                    StockGroupItem.is_removed == 0,
                )
            )
            return [row[0] for row in result.all()]

    async def get_by_id(self, group_id: str) -> Any | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockGroup).where(StockGroup.id == int(group_id))
            )
            g = result.scalars().first()
            if not g:
                return None
            return {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "user_id": g.user_id,
            }

    async def list_by_user(self, user_id: str) -> list[dict]:
        return await self.list_groups(int(user_id))

    async def create(self, group_data: dict) -> dict:
        result = await self.create_group(
            name=group_data.get("name", ""),
            description=group_data.get("description", ""),
            user_id=group_data.get("user_id", 1),
        )
        return result or {}

    async def add_symbol_to_group(
        self, group_id: int, symbol: str, user_id: int = 1
    ) -> bool:
        async with self._session_factory() as session:
            try:
                existing = await session.execute(
                    select(StockGroupItem).where(
                        StockGroupItem.group_id == group_id,
                        StockGroupItem.symbol == symbol,
                        StockGroupItem.user_id == user_id,
                    )
                )
                if existing.scalars().first():
                    return True

                item = StockGroupItem(group_id=group_id, symbol=symbol, user_id=user_id)
                session.add(item)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False

    async def remove_symbol_from_group(
        self, group_id: int, symbol: str, user_id: int = 1
    ) -> bool:
        async with self._session_factory() as session:
            stmt = update(StockGroupItem).where(
                StockGroupItem.group_id == group_id,
                StockGroupItem.symbol == symbol,
                StockGroupItem.user_id == user_id,
            ).values(is_removed=1)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def add_to_group(self, group_id: str, symbol: str, user_id: int = 1) -> bool:
        return await self.add_symbol_to_group(int(group_id), symbol, user_id)


class AsyncMySQLSignalFlagPoolRepository(AsyncRepositoryBase):
    """Async implementation of SignalFlagPoolRepository.

    Core methods:
    - list_dates() - List available pool dates
    - get_pool() - Get signal pool for a specific date
    - upsert_pool() - Insert or update pool entries
    """

    async def list_dates(self, *, limit: int = 120) -> list[str]:
        async with self._session_factory() as session:
            stmt = (
                select(SignalFlagPool.pool_date)
                .group_by(SignalFlagPool.pool_date)
                .order_by(desc(SignalFlagPool.pool_date))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [str(row[0])[:10] for row in result.all()]

    async def get_pool(self, pool_date: str) -> list[dict[str, Any]]:
        d = (pool_date or "")[:10]
        async with self._session_factory() as session:
            stmt = (
                select(SignalFlagPool)
                .where(SignalFlagPool.pool_date == d)
                .order_by(desc(SignalFlagPool.amount), SignalFlagPool.code)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            out = []
            for r in rows:
                item = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                for k in ("signal_strategies", "signal_strategies_sell", "long_horizon", "mid_horizon", "short_horizon", "extra_snapshot"):
                    if k in item and isinstance(item[k], str):
                        try:
                            item[k] = json.loads(item[k])
                        except (json.JSONDecodeError, TypeError):
                            item[k] = [] if "strategies" in k else {}
                out.append(item)
            return out

    async def upsert_pool(self, entries: list[dict[str, Any]]) -> int:
        async with self._session_factory() as session:
            count = 0
            for entry in entries:
                stmt = select(SignalFlagPool).where(
                    SignalFlagPool.pool_date == entry.get("pool_date", ""),
                    SignalFlagPool.code == entry.get("code", ""),
                )
                existing = await session.execute(stmt)
                existing_obj = existing.scalars().first()

                if existing_obj:
                    for key, value in entry.items():
                        setattr(existing_obj, key, value)
                    count += 1
                else:
                    session.add(SignalFlagPool(**entry))
                    count += 1
            await session.commit()
            return count


class AsyncMySQLTradingRepository(AsyncRepositoryBase):
    """Async implementation of TradingRepository.

    Core methods:
    - list_open_trades() - Get all open trades
    - create_trade() - Create a new trade
    - close_trade() - Close an existing trade
    - list_orders() - Get orders for a trade
    """

    async def list_open_trades(self, exchange: str = "binance") -> list[dict]:
        async with self._session_factory() as session:
            stmt = select(FTTrade).where(
                FTTrade.exchange == exchange,
                FTTrade.is_open == 1
            )
            result = await session.execute(stmt)
            return [
                {
                    "id": t.id,
                    "pair": t.pair,
                    "open_rate": t.open_rate,
                    "amount": t.amount,
                    "stake_amount": t.stake_amount,
                    "open_date": t.open_date.isoformat() if t.open_date else None,
                }
                for t in result.scalars().all()
            ]

    async def create_trade(self, trade_data: dict) -> int:
        async with self._session_factory() as session:
            trade = FTTrade(
                exchange=trade_data.get("exchange", "binance"),
                pair=trade_data.get("pair", ""),
                base_currency=trade_data.get("base_currency"),
                stake_currency=trade_data.get("stake_currency"),
                open_date=trade_data.get("open_date", datetime.now()),
                open_rate=trade_data.get("open_rate", 0.0),
                open_rate_requested=trade_data.get("open_rate_requested"),
                stake_amount=trade_data.get("stake_amount", 0.0),
                amount=trade_data.get("amount", 0.0),
                strategy=trade_data.get("strategy"),
                enter_tag=trade_data.get("enter_tag"),
            )
            session.add(trade)
            await session.commit()
            return trade.id

    async def close_trade(self, trade_id: int, close_rate: float, close_profit: float) -> bool:
        async with self._session_factory() as session:
            stmt = select(FTTrade).where(FTTrade.id == trade_id)
            result = await session.execute(stmt)
            trade = result.scalars().first()
            if not trade:
                return False
            trade.close_rate = close_rate
            trade.close_profit = close_profit
            trade.close_date = datetime.now()
            trade.is_open = 0
            await session.commit()
            return True

    async def list_orders(self, trade_id: int) -> list[dict]:
        async with self._session_factory() as session:
            stmt = select(FTOrder).where(FTOrder.ft_trade_id == trade_id)
            result = await session.execute(stmt)
            return [
                {
                    "id": o.id,
                    "order_id": o.order_id,
                    "ft_order_side": o.ft_order_side,
                    "ft_amount": o.ft_amount,
                    "ft_price": o.ft_price,
                    "status": o.status,
                }
                for o in result.scalars().all()
            ]


class AsyncMySQLInvestmentManagerRepository(AsyncRepositoryBase):
    """Async implementation of InvestmentManagerRepository.

    Core methods:
    - list_managers() - List all investment managers
    - get_manager() - Get manager by ID
    - create_manager() - Create new manager
    - update_nav() - Update NAV record
    - list_trades() - List manager trades
    - list_holdings() - List current holdings
    """

    async def list_managers(self, active_only: bool = True) -> list[dict]:
        async with self._session_factory() as session:
            stmt = select(InvestmentManager)
            if active_only:
                stmt = stmt.where(InvestmentManager.active == 1)
            result = await session.execute(stmt)
            return [
                {
                    "manager_id": m.manager_id,
                    "strategy_id": m.strategy_id,
                    "name": m.name,
                    "bio": m.bio,
                    "cohort": m.cohort,
                    "active": m.active,
                }
                for m in result.scalars().all()
            ]

    async def get_manager(self, manager_id: str) -> dict | None:
        async with self._session_factory() as session:
            stmt = select(InvestmentManager).where(InvestmentManager.manager_id == manager_id)
            result = await session.execute(stmt)
            m = result.scalars().first()
            if not m:
                return None
            return {
                "manager_id": m.manager_id,
                "strategy_id": m.strategy_id,
                "name": m.name,
                "bio": m.bio,
                "cohort": m.cohort,
                "active": m.active,
            }

    async def create_manager(self, manager_data: dict) -> bool:
        async with self._session_factory() as session:
            try:
                manager = InvestmentManager(
                    manager_id=manager_data.get("manager_id", ""),
                    strategy_id=manager_data.get("strategy_id", ""),
                    name=manager_data.get("name", ""),
                    bio=manager_data.get("bio", ""),
                    cohort=manager_data.get("cohort", ""),
                    active=manager_data.get("active", 0),
                )
                session.add(manager)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False

    async def update_nav(self, manager_id: str, nav_date: str, equity: float, cash: float) -> bool:
        async with self._session_factory() as session:
            stmt = select(ManagerNAV).where(
                ManagerNAV.manager_id == manager_id,
                ManagerNAV.nav_date == nav_date,
            )
            result = await session.execute(stmt)
            nav = result.scalars().first()

            if nav:
                nav.equity = equity
                nav.cash = cash
            else:
                session.add(ManagerNAV(
                    manager_id=manager_id,
                    nav_date=nav_date,
                    equity=equity,
                    cash=cash,
                ))
            await session.commit()
            return True

    async def list_trades(self, manager_id: str, limit: int = 100) -> list[dict]:
        async with self._session_factory() as session:
            stmt = (
                select(ManagerTrade)
                .where(ManagerTrade.manager_id == manager_id)
                .order_by(desc(ManagerTrade.trade_date))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [
                {
                    "trade_id": t.trade_id,
                    "trade_date": t.trade_date,
                    "symbol": t.symbol,
                    "action": t.action,
                    "price": t.price,
                    "shares": t.shares,
                }
                for t in result.scalars().all()
            ]

    async def list_holdings(self, manager_id: str, snap_date: str) -> list[dict]:
        async with self._session_factory() as session:
            stmt = select(ManagerHoldingsSnap).where(
                ManagerHoldingsSnap.manager_id == manager_id,
                ManagerHoldingsSnap.snap_date == snap_date,
            )
            result = await session.execute(stmt)
            return [
                {
                    "symbol": h.symbol,
                    "shares": h.shares,
                    "avg_cost": h.avg_cost,
                    "market_price": h.market_price,
                    "market_value": h.market_value,
                    "weight": h.weight,
                }
                for h in result.scalars().all()
            ]


__all__ = [
    "AsyncRepositoryBase",
    "AsyncMySQLUserRepository",
    "AsyncMySQLWatchlistRepository",
    "AsyncMySQLStockGroupRepository",
    "AsyncMySQLSignalFlagPoolRepository",
    "AsyncMySQLTradingRepository",
    "AsyncMySQLInvestmentManagerRepository",
]
