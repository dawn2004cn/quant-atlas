"""Base class providing session factory and seeding logic for MySQL repositories.

This file contains the MySQLRepositoryBase class extracted from the original
`mysql_repositories.py`.  All other repository implementations should inherit
from this base.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import pymysql.err
from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError as SAOperationalError

from app.core.logger import get_logger
from app.infrastructure.database.orm import bootstrap_schema

from ....core.password_hash import hash_password
from ....domain.ports import StockGroupRepository, UserRepository, WatchlistRepository
from ....domain.role_catalog import PROTECTED_DEMO_USERNAMES
from ....domain.shared.value_objects import UserAccount
from ...database.models.auth import Role, User
from ...database.models.market import StockGroup, StockGroupItem, Watchlist
from ..common.user_mapper import user_row_to_account

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

        users_to_sync = session.scalars(select(User).where(User.role_id is None)).all()
        for u in users_to_sync:
            u.role_id = role_map.get(u.role.lower(), role_map.get("viewer"))
        session.flush()

        # Sync role column from role_id for all users that have role_id set
        users_with_role_id = session.scalars(select(User).where(User.role_id is not None)).all()
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
                new_user = User(username=uname, password_hash=self._hash(pwd), role=role_code, role_id=rid)
                session.add(new_user)
        session.flush()

    def _seed_users(self, session) -> None:
        if session.query(func.count(User.id)).scalar() > 5:
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
                is_default=int(group.get("is_default", 0)),
            )
            session.add(g)
            session.flush()
            id_map[int(group["id"]) ]= g.id
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

"""
We have split the code base
"""
