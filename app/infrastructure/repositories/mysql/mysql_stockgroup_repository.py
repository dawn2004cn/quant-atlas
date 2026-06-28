from __future__ import annotations
"""MySQL StockGroup Repository."""


from typing import Any

from sqlalchemy import select, and_, desc

from ....domain.ports import StockGroupRepository
from ...database.models.market import StockGroup, StockGroupItem
from .mysql_repositories import MySQLRepositoryBase


from app.core.logger import get_logger
from app.core.query_limits import MAX_STOCK_GROUP_SYMBOLS

logger = get_logger(__name__)


class MySQLStockGroupRepository(MySQLRepositoryBase, StockGroupRepository):
    """MySQL implementation of StockGroupRepository."""

    def list_groups(self, user_id: int = 1) -> list[dict[str, Any]]:
        """List stock groups for a user."""
        session = self._session_factory()
        try:
            groups = session.scalars(
                select(StockGroup)
                .where(StockGroup.user_id == user_id)
                .order_by(desc(StockGroup.is_default), StockGroup.id)
            ).all()
            return [
                {"id": g.id, "name": g.name, "description": g.description or "", "is_default": bool(g.is_default), "color": getattr(g, 'color', '#3B82F6')}
                for g in groups
            ]
        finally:
            session.close()
            self._session_factory.remove()

    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> dict | None:
        """Create stock group for a user."""
        session = self._session_factory()
        try:
            group = StockGroup(
                name=name,
                description=description,
                is_default=0,
                user_id=user_id,
                color=color or '#3B82F6'
            )
            session.add(group)
            session.commit()
            return {"id": group.id, "name": group.name, "description": group.description, "is_default": False, "color": group.color}
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()
            self._session_factory.remove()

    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> bool:
        """Update stock group."""
        session = self._session_factory()
        try:
            group = session.get(StockGroup, group_id)
            if not group or group.is_default or group.user_id != user_id:
                return False
            group.name = name
            group.description = description
            if color:
                group.color = color
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        """Delete stock group."""
        session = self._session_factory()
        try:
            group = session.get(StockGroup, group_id)
            if not group or group.is_default or group.user_id != user_id:
                return False
            session.delete(group)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        """List symbols in a group."""
        session = self._session_factory()
        try:
            stmt = select(StockGroupItem.symbol).where(
                and_(
                    StockGroupItem.group_id == group_id,
                    StockGroupItem.user_id == user_id,
                    StockGroupItem.is_removed == 0
                )
            ).order_by(StockGroupItem.symbol).limit(MAX_STOCK_GROUP_SYMBOLS)
            res = session.scalars(stmt).all()
            # Return raw symbols (could be "SH600519" or "600519" or "BJ920873")
            return [str(s).strip() for s in res if str(s).strip()]
        except Exception as e:
            logger.error(f"Error listing group symbols: {e}")
            return []
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_id(self, group_id: str) -> dict | None:
        """Get stock group by ID."""
        session = self._session_factory()
        try:
            group = session.query(StockGroup).filter(StockGroup.id == int(group_id)).first()
            if not group:
                return None
            return {
                "id": group.id,
                "name": group.name,
                "description": group.description or "",
                "color": group.color or "",
            }
        finally:
            session.close()
            self._session_factory.remove()

    def list_by_user(self, user_id: str) -> list[dict]:
        """List stock groups for user."""
        return self.list_groups(int(user_id) if str(user_id).isdigit() else 1)

    def create(self, group_data: dict) -> dict:
        """Create stock group (alias for compatibility)."""
        result = self.create_group(
            name=group_data.get("name", "default"),
            description=group_data.get("description", ""),
            color=group_data.get("color", "#3B82F6"),
            user_id=int(group_data.get("user_id", 1)) if str(group_data.get("user_id", "1")).isdigit() else 1
        )
        return result or {"name": group_data.get("name", "default")}

    def add_symbol_to_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        """Add symbol to group."""
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        session = self._session_factory()
        try:
            group = session.get(StockGroup, group_id)
            if not group or group.user_id != user_id:
                return False

            normalized = SymbolNormalizer.to_db_code(str(symbol))
            existing = session.execute(
                select(StockGroupItem).where(
                    and_(StockGroupItem.group_id == group_id, StockGroupItem.symbol == normalized, StockGroupItem.user_id == user_id)
                )
            ).scalar_one_or_none()

            if existing:
                existing.is_removed = 0
            else:
                session.merge(StockGroupItem(group_id=group_id, symbol=normalized, user_id=user_id))

            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def remove_symbol_from_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        """Remove symbol from group."""
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        session = self._session_factory()
        try:
            normalized = SymbolNormalizer.to_db_code(str(symbol))
            item = session.execute(
                select(StockGroupItem).where(
                    and_(StockGroupItem.group_id == group_id, StockGroupItem.symbol == normalized, StockGroupItem.user_id == user_id, StockGroupItem.is_removed == 0)
                )
            ).scalar_one_or_none()
            if item:
                item.is_removed = 1
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def add_to_group(self, group_id: str, symbol: str, user_id: int = 1) -> bool:
        """Add symbol to group (alias for compatibility)."""
        return self.add_symbol_to_group(int(group_id), symbol, user_id)
