from __future__ import annotations
"""MySQL Watchlist Repository."""


import logging
from typing import Any

from ....domain.ports import WatchlistRepository
from ...database.models.market import Watchlist
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
from .mysql_repositories import MySQLRepositoryBase


from app.core.logger import get_logger
from app.core.query_limits import MAX_WATCHLIST_SYMBOLS

logger = get_logger(__name__)


class MySQLWatchlistRepository(MySQLRepositoryBase, WatchlistRepository):
    """MySQL implementation of WatchlistRepository."""

    def list_symbols(self, user_id: int = 1) -> list[str]:
        session = self._session_factory()
        try:
            watchlist = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .limit(MAX_WATCHLIST_SYMBOLS)
                .all()
            )
            return [w.symbol for w in watchlist]
        finally:
            session.close()
            self._session_factory.remove()

    def save_symbols(self, user_id: int, symbols: list[str]) -> None:
        session = self._session_factory()
        try:
            session.query(Watchlist).filter(Watchlist.user_id == user_id).delete()
            for symbol in symbols:
                normalized = SymbolNormalizer.to_db_code(symbol)
                session.add(Watchlist(user_id=user_id, symbol=normalized))
            session.commit()
        finally:
            session.close()
            self._session_factory.remove()

    def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        session = self._session_factory()
        try:
            normalized = SymbolNormalizer.to_db_code(symbol)
            existing = session.query(Watchlist).filter(
                Watchlist.user_id == user_id, Watchlist.symbol == normalized
            ).first()
            if existing:
                return True
            session.add(Watchlist(user_id=user_id, symbol=normalized))
            session.commit()
            return True
        except Exception:
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        session = self._session_factory()
        try:
            normalized = SymbolNormalizer.to_db_code(symbol)
            item = session.query(Watchlist).filter(
                Watchlist.user_id == user_id, Watchlist.symbol == normalized
            ).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_user(self, user_id: str) -> list[dict]:
        session = self._session_factory()
        try:
            items = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == int(user_id))
                .limit(MAX_WATCHLIST_SYMBOLS)
                .all()
            )
            return [{"symbol": w.symbol, "created_at": str(w.created_at)} for w in items]
        finally:
            session.close()
            self._session_factory.remove()

    def add_stock(self, user_id: str, stock_code: str, watchlist_name: str = "default") -> dict:
        return {"symbol": stock_code, "user_id": user_id, "watchlist": watchlist_name}

    def remove_stock(self, user_id: str, stock_code: str, watchlist_name: str = "default") -> bool:
        return True

    def list_groups(self, user_id: int = 1) -> list[dict]:
        return []

    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> dict | None:
        return {"name": name, "description": description, "color": color}

    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> bool:
        return True

    def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        return True

    def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        return []