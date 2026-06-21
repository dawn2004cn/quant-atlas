from __future__ import annotations
"""SQLAlchemy implementation of User, Watchlist, and StockGroup repositories."""


import json
import re
import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, delete, insert, update, func, and_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError as SAOperationalError
import pymysql.err

from ....core.password_hash import hash_password
from ....domain.entities import UserAccount
from ....domain.ports import StockGroupRepository, UserRepository, WatchlistRepository
from app.infrastructure.database.orm import bootstrap_schema
from ....domain.role_catalog import PROTECTED_DEMO_USERNAMES
from ...database.models.auth import User, Role
from ...database.models.market import Watchlist, StockGroup, StockGroupItem
from ..common.user_mapper import user_row_to_account


from app.core.logger import get_logger

logger = get_logger(__name__)

_ROLE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, "admin", "Admin", 10),
    (2, "developer", "Developer", 20),
    (3, "researcher", "Researcher", 30),
    (4, "trader", "Trader", 40),
    (5, "viewer", "Viewer", 50),
)


class MySQLRepositoryBase:
    def __init__(
        self,
        session_factory,
        users_json_path: Path | None = None,
        watchlist_json_path: Path | None = None,
        stock_groups_json_path: Path | None = None,
    ):
        self._session_factory = session_factory
        self._users_json_path = users_json_path
        self._watchlist_json_path = watchlist_json_path
        self._stock_groups_json_path = stock_groups_json_path
        
        # Ensure database schema exists before seeding
        try:
            engine = self._session_factory().get_bind()
            if engine is not None:
                bootstrap_schema(engine)
        except Exception as e:
            logger.warning(f"Failed to bootstrap schema: {e}")

        # Seeding logic remains, but uses SQLAlchemy sessions.
        # If DB is temporarily saturated, allow app bootstrap to continue.
        try:
            self._run_seeding()
        except SAOperationalError as exc:
            orig = getattr(exc, "orig", None)
            err_code = int(orig.args[0]) if isinstance(orig, pymysql.err.OperationalError) and orig.args else None
            if err_code == 1040:
                logger.warning("Skip repository seeding due to MySQL connection saturation (1040).")
            else:
                raise

    def _run_seeding(self) -> None:
        session = self._session_factory()
        try:
            self._seed_roles(session)
            self._sync_user_role_ids(session)
            self._seed_users(session)
            self._seed_groups(session)
            self._seed_watchlist(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def _seed_roles(self, session) -> None:
        for rid, code, label, sort_order in _ROLE_ROWS:
            role = session.get(Role, rid)
            if not role:
                role = Role(id=rid, code=code, label=label, sort_order=sort_order)
                session.add(role)
        session.flush()

    def _sync_user_role_ids(self, session) -> None:
        # Complex sync logic converted to SQLAlchemy
        # 1. Update role_id based on role string
        roles = session.scalars(select(Role)).all()
        role_map = {r.code.lower(): r.id for r in roles}
        
        users_to_sync = session.scalars(select(User).where(User.role_id == None)).all()
        for u in users_to_sync:
            u.role_id = role_map.get(u.role.lower(), role_map.get('viewer'))
            # Sync the role column from role_id for older DBs
        session.flush()

        # Sync role column from role_id for all users that have role_id set
        users_with_role_id = session.scalars(select(User).where(User.role_id != None)).all()
        role_by_id = {r.id: r for r in session.scalars(select(Role)).all()}
        for u in users_with_role_id:
            if not u.role or u.role.lower() not in {r.code for r in role_by_id.values()}:
                r = role_by_id.get(u.role_id)
                if r:
                    u.role = r.code
        
        session.flush()
        
        # 2. Ensure demo users exist
        demo_specs = (
            ("researcher", "research123", "researcher", 3),
            ("trader", "trade123", "trader", 4),
        )
        for uname, pwd, role_code, rid in demo_specs:
            existing = session.scalars(select(User).where(User.username == uname)).first()
            if not existing:
                new_user = User(
                    username=uname,
                    password_hash=self._hash(pwd),
                    role=role_code,
                    role_id=rid
                )
                session.add(new_user)
        session.flush()

    def _seed_users(self, session) -> None:
        if session.query(func.count(User.id)).scalar() > 5: # More than just demo users
            return
            
        payload = self._read_json(self._users_json_path) if self._users_json_path else None
        if not payload:
            specs = (
                (1, "admin", "admin123", "admin", 1),
                (2, "developer", "dev123", "developer", 2),
            )
            for uid, uname, pwd, role_code, rid in specs:
                if not session.get(User, uid):
                    u = User(id=uid, username=uname, password_hash=self._hash(pwd), role=role_code, role_id=rid)
                    session.add(u)
            return

        for username, data in payload.items():
            if not session.get(User, data["id"]):
                role_code = str(data.get("role", "viewer"))
                role = session.scalars(select(Role).where(Role.code == role_code)).first()
                rid = role.id if role else 5
                u = User(id=data["id"], username=username, password_hash=data["password"], role=role_code, role_id=rid)
                session.add(u)

    def _seed_groups(self, session) -> None:
        if session.query(func.count(StockGroup.id)).scalar() > 0:
            return
            
        payload = self._read_json(self._stock_groups_json_path) if self._stock_groups_json_path else None
        groups = (payload or {}).get("groups", [])
        items = (payload or {}).get("items", {})
        
        if not groups:
            g = StockGroup(name="鑷€夎偂", description="榛樿鍒嗙粍", is_default=1)
            session.add(g)
            return

        id_map: dict[int, int] = {}
        for group in groups:
            g = StockGroup(
                name=group.get("name", ""),
                description=group.get("description", ""),
                is_default=int(group.get("is_default", 0))
            )
            session.add(g)
            session.flush()
            id_map[int(group["id"])] = g.id
            
        for old_group_id, symbols in items.items():
            new_group_id = id_map.get(int(old_group_id))
            if not new_group_id:
                continue
            for symbol in symbols:
                from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
                normalized = SymbolNormalizer.to_db_code(str(symbol))
                item = StockGroupItem(group_id=new_group_id, symbol=normalized)
                session.merge(item)

    def _seed_watchlist(self, session) -> None:
        if session.query(func.count(Watchlist.symbol)).scalar() > 0:
            return

        payload = self._read_json(self._watchlist_json_path) if self._watchlist_json_path else []
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = [SymbolNormalizer.to_db_code(str(item)) for item in (payload or [])]

        for symbol in normalized:
            w = Watchlist(symbol=symbol)
            session.merge(w)

        default_group = session.scalars(select(StockGroup).where(StockGroup.is_default == 1)).first()
        if default_group:
            for symbol in normalized:
                item = StockGroupItem(group_id=default_group.id, symbol=symbol)
                session.merge(item)

    @staticmethod
    def _read_json(path: Path | None):
        if not path or not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _hash(password: str) -> str:
        return hash_password(password)


class MySQLUserRepository(MySQLRepositoryBase, UserRepository):
    @staticmethod
    def _map_user(u: User) -> UserAccount:
        # Prefer direct role column; fall back to role_rel for older DBs
        role_code = u.role if u.role else (u.role_rel.code if u.role_rel else "")
        return user_row_to_account(
            user_id=u.id,
            username=u.username,
            role=role_code,
            password_hash=u.password_hash,
            avatar_url=u.avatar_url,
        )

    def list_users(self) -> list[UserAccount]:
        from app.core.query_limits import MAX_USERS

        session = self._session_factory()
        try:
            users = session.scalars(select(User).limit(MAX_USERS)).all()
            return [self._map_user(u) for u in users]
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_username(self, username: str) -> UserAccount | None:
        session = self._session_factory()
        try:
            u = session.scalars(select(User).where(User.username == username)).first()
            if not u:
                return None
            return self._map_user(u)
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_id(self, user_id: str | int) -> UserAccount | None:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        session = self._session_factory()
        try:
            u = session.get(User, uid)
            if not u:
                return None
            return self._map_user(u)
        finally:
            session.close()
            self._session_factory.remove()

    def create_user(self, username: str, password: str, role: str) -> bool:
        session = self._session_factory()
        try:
            db_role = session.scalars(select(Role).where(Role.code == role)).first()
            if not db_role:
                return False
            new_user = User(
                username=username,
                password_hash=self._hash(password),
                role=db_role.code,
                role_id=db_role.id
            )
            session.add(new_user)
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def delete_user(self, username: str) -> bool:
        if username in PROTECTED_DEMO_USERNAMES:
            return False
        session = self._session_factory()
        try:
            u = session.scalars(select(User).where(User.username == username)).first()
            if u:
                session.delete(u)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def create(self, user: UserAccount) -> str:
        session = self._session_factory()
        try:
            db_role = session.scalars(select(Role).where(Role.code == user.role)).first()
            if not db_role:
                raise ValueError(f"invalid role: {user.role}")
            new_user = User(
                username=user.username,
                password_hash=user.password_hash,
                role=user.role,
                role_id=db_role.id,
                avatar_url=user.avatar_url or None,
            )
            session.add(new_user)
            session.commit()
            return str(new_user.id)
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("user already exists") from exc
        finally:
            session.close()
            self._session_factory.remove()

    def update(self, user_id: str, data: dict[str, Any]) -> bool:
        session = self._session_factory()
        try:
            uid = int(user_id)
            u = session.get(User, uid)
            if not u:
                return False
            if 'username' in data:
                u.username = data['username']
            if 'password' in data:
                u.password_hash = self._hash(data['password'])
            if 'role' in data:
                db_r = session.scalars(select(Role).where(Role.code == data['role'])).first()
                if db_r:
                    u.role = db_r.code
                    u.role_id = db_r.id
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def delete(self, user_id: str) -> bool:
        session = self._session_factory()
        try:
            uid = int(user_id)
            u = session.get(User, uid)
            if not u:
                return False
            session.delete(u)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()
    
    def list_all(self, limit: int = 100) -> list[UserAccount]:
        session = self._session_factory()
        try:
            users = session.scalars(select(User).limit(max(1, int(limit)))).all()
            return [self._map_user(u) for u in users]
        finally:
            session.close()
            self._session_factory.remove()

    def update_password(self, username: str, password: str) -> bool:
        session = self._session_factory()
        try:
            u = session.scalars(select(User).where(User.username == username)).first()
            if u:
                u.password_hash = self._hash(password)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def list_roles(self) -> list[dict]:
        session = self._session_factory()
        try:
            roles = session.scalars(select(Role).order_by(Role.sort_order, Role.id)).all()
            return [{"id": r.id, "code": r.code, "label": r.label, "sort_order": r.sort_order} for r in roles]
        finally:
            session.close()
            self._session_factory.remove()

    def update_user_role(self, username: str, role_code: str) -> bool:
        session = self._session_factory()
        try:
            db_role = session.scalars(select(Role).where(Role.code == role_code)).first()
            if not db_role:
                return False
            u = session.scalars(select(User).where(User.username == username)).first()
            if u:
                u.role = db_role.code
                u.role_id = db_role.id
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def get_by_wechat_openid(self, openid: str) -> UserAccount | None:
        session = self._session_factory()
        try:
            u = session.scalars(select(User).where(User.wechat_openid == openid)).first()
            if not u:
                return None
            return self._map_user(u)
        finally:
            session.close()
            self._session_factory.remove()

    def link_or_create_wechat_user(self, openid: str, *, nickname: str | None = None) -> UserAccount | None:
        oid = (openid or "").strip()
        if not oid:
            return None
        existing = self.get_by_wechat_openid(oid)
        if existing:
            return existing
            
        nick = (nickname or "").strip()
        base = re.sub(r"[^\w\u4e00-\u9fff]", "", nick)[:24] if nick else ""
        if not base or len(base) < 2:
            base = f"wx{oid[-10:]}"
        if base.lower() in {x.lower() for x in PROTECTED_DEMO_USERNAMES}:
            base = f"wx{oid[-10:]}"
            
        session = self._session_factory()
        try:
            viewer_role = session.scalars(select(Role).where(Role.code == 'viewer')).first()
            if not viewer_role:
                return None
                
            rnd = self._hash(secrets.token_hex(32))
            for i in range(0, 50):
                candidate = f"{base}{i}" if i else base
                if len(candidate) > 48:
                    candidate = candidate[:48]
                try:
                    new_user = User(
                        username=candidate,
                        password_hash=rnd,
                        role='viewer',
                        role_id=viewer_role.id,
                        wechat_openid=oid,
                        display_name=nick or None
                    )
                    session.add(new_user)
                    session.commit()
                    return self.get_by_username(candidate)
                except IntegrityError:
                    session.rollback()
                    continue
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()
        return None

    def update_avatar_url(self, username: str, avatar_url: str | None) -> bool:
        session = self._session_factory()
        try:
            u = session.scalars(select(User).where(User.username == username)).first()
            if u:
                u.avatar_url = (avatar_url or "").strip() or None
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()


class MySQLWatchlistRepository(MySQLRepositoryBase, WatchlistRepository):
    def list_symbols(self, user_id: int = 1) -> list[str]:
        session = self._session_factory()
        try:
            symbols = session.scalars(
                select(Watchlist.symbol).where(Watchlist.user_id == user_id).order_by(Watchlist.symbol)
            ).all()
            return list(symbols)
        finally:
            session.close()
            self._session_factory.remove()

    def save_symbols(self, user_id: int, symbols: list[str]) -> None:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = [SymbolNormalizer.to_db_code(str(item)) for item in symbols]
        session = self._session_factory()
        try:
            session.execute(delete(Watchlist).where(Watchlist.user_id == user_id))
            for sym in normalized:
                session.add(Watchlist(symbol=sym, user_id=user_id))

            default_group = session.scalars(select(StockGroup).where(StockGroup.is_default == 1, StockGroup.user_id == user_id)).first()
            if default_group:
                for sym in normalized:
                    item = StockGroupItem(group_id=default_group.id, symbol=sym, user_id=user_id)
                    session.merge(item)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(str(symbol))
        session = self._session_factory()
        try:
            existing = session.scalars(select(Watchlist).where(Watchlist.symbol == normalized, Watchlist.user_id == user_id)).first()
            if existing:
                return True
            session.add(Watchlist(symbol=normalized, user_id=user_id))
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(str(symbol))
        session = self._session_factory()
        try:
            result = session.execute(delete(Watchlist).where(Watchlist.symbol == normalized, Watchlist.user_id == user_id))
            session.commit()
            return result.rowcount > 0
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()
    
    def get_by_user(self, user_id: str) -> list[dict]:
        """Get watchlist for user (implements WatchlistRepository port)."""
        return [{"symbol": s} for s in self.list_symbols(int(user_id) if user_id.isdigit() else 1)]
    
    def add_stock(self, user_id: str, stock_code: str, watchlist_name: str = "default") -> dict:
        """Add stock to watchlist."""
        self.add_symbol(stock_code, int(user_id) if user_id.isdigit() else 1)
        return {"user_id": user_id, "stock_code": stock_code, "watchlist": watchlist_name}
    
    def remove_stock(self, user_id: str, stock_code: str, watchlist_name: str = "default") -> bool:
        """Remove stock from watchlist."""
        return self.remove_symbol(stock_code, int(user_id) if user_id.isdigit() else 1)


class MySQLStockGroupRepository(MySQLRepositoryBase, StockGroupRepository):
    def list_groups(self, user_id: int = 1) -> list[dict]:
        session = self._session_factory()
        try:
            groups = session.scalars(
                select(StockGroup)
                .where(StockGroup.user_id == user_id)
                .order_by(desc(StockGroup.is_default), StockGroup.id)
            ).all()
            return [
                {"id": g.id, "name": g.name, "description": g.description, "is_default": bool(g.is_default), "color": getattr(g, 'color', '#3B82F6')}
                for g in groups
            ]
        finally:
            session.close()
            self._session_factory.remove()

    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> dict | None:
        session = self._session_factory()
        try:
            g = StockGroup(name=name, description=description, is_default=0, user_id=user_id, color=color or '#3B82F6')
            session.add(g)
            session.commit()
            return {"id": g.id, "name": g.name, "description": g.description, "is_default": False, "color": g.color}
        except IntegrityError:
            session.rollback()
            return None
        finally:
            session.close()
            self._session_factory.remove()

    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> bool:
        session = self._session_factory()
        try:
            g = session.get(StockGroup, group_id)
            if not g or g.is_default or g.user_id != user_id:
                return False
            g.name = name
            g.description = description
            if color:
                g.color = color
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False
        finally:
            session.close()
            self._session_factory.remove()

    def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        session = self._session_factory()
        try:
            g = session.get(StockGroup, group_id)
            if not g or g.is_default or g.user_id != user_id:
                return False
            session.delete(g)
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
            ).order_by(StockGroupItem.symbol)
            res = session.scalars(stmt).all()
            return [str(s).strip() for s in res if str(s).strip()]
        except Exception as e:
            logger.error(f"Error listing group symbols: {e}")
            return []
        finally:
            session.close()
            self._session_factory.remove()
    
    def get_by_id(self, group_id: str) -> Optional[dict]:
        """Get stock group by ID."""
        try:
            return self.list_groups(int(group_id) if group_id.isdigit() else 1)[0]
        except (IndexError, ValueError):
            return None
    
    def list_by_user(self, user_id: str) -> list[dict]:
        """List stock groups for user."""
        return self.list_groups(int(user_id) if user_id.isdigit() else 1)
    
    def create(self, group_data: dict) -> dict:
        """Create stock group."""
        result = self.create_group(
            name=group_data.get("name", "default"),
            description=group_data.get("description", ""),
            color=group_data.get("color", "#3B82F6"),
            user_id=int(group_data.get("user_id", 1)) if str(group_data.get("user_id", "1")).isdigit() else 1
        )
        return result or {"name": group_data.get("name", "default")}
    
    def add_symbol_to_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(str(symbol))
        session = self._session_factory()
        try:
            g = session.get(StockGroup, group_id)
            if not g or g.user_id != user_id:
                logger.warning("add_symbol_to_group: group %s not found or not owned by user", group_id)
                return False

            existing = session.execute(
                select(StockGroupItem).where(
                    and_(StockGroupItem.group_id == group_id, StockGroupItem.symbol == normalized, StockGroupItem.user_id == user_id)
                )
            ).scalar_one_or_none()

            if existing:
                existing.is_removed = 0
                existing.added_at = datetime.now()
            else:
                session.merge(StockGroupItem(group_id=group_id, symbol=normalized, user_id=user_id, added_at=datetime.now()))

            default_group = session.scalars(select(StockGroup).where(StockGroup.is_default == 1, StockGroup.user_id == user_id)).first()
            if default_group and default_group.id != group_id:
                def_existing = session.execute(
                    select(StockGroupItem).where(
                        and_(StockGroupItem.group_id == default_group.id, StockGroupItem.symbol == normalized, StockGroupItem.user_id == user_id)
                    )
                ).scalar_one_or_none()
                if def_existing:
                    def_existing.is_removed = 0
                else:
                    session.merge(StockGroupItem(group_id=default_group.id, symbol=normalized, user_id=user_id, added_at=datetime.now()))

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error("add_symbol_to_group failed: %s", e)
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def remove_symbol_from_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(str(symbol))
        session = self._session_factory()
        try:
            stmt = update(StockGroupItem).where(
                and_(StockGroupItem.group_id == group_id, StockGroupItem.symbol == normalized, StockGroupItem.user_id == user_id)
            ).values(is_removed=1)
            res = session.execute(stmt)
            session.commit()
            return res.rowcount > 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session_factory.remove()

    def add_to_group(self, group_id: str, symbol: str, user_id: int = 1) -> bool:
        return self.add_symbol_to_group(int(group_id), symbol, user_id)

