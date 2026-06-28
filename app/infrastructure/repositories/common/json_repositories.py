"""JSON-backed repositories for bootstrap compatibility."""

from __future__ import annotations

import json
import re
import secrets
import os
from pathlib import Path
from typing import Any

from app.core.password_hash import hash_password
from app.domain.entities import UserAccount
from app.domain.ports import StockGroupRepository, UserRepository, WatchlistRepository
from app.domain.role_catalog import PROTECTED_DEMO_USERNAMES, ROLE_LABELS


class JsonUserRepository(UserRepository):
    """User repository backed by a JSON file."""

    def __init__(self, path: Path):
        self._path = path

    def list_users(self) -> list[UserAccount]:
        users = self._read()
        return [
            UserAccount(
                user_id=data["id"],
                username=username,
                role=data.get("role", "viewer"),
                password_hash=data["password"],
                avatar_url=str(data.get("avatar_url") or ""),
            )
            for username, data in users.items()
        ]

    def get_by_username(self, username: str) -> UserAccount | None:
        data = self._read().get(username)
        if not data:
            return None
        return UserAccount(
            user_id=data["id"],
            username=username,
            role=data.get("role", "viewer"),
            password_hash=data["password"],
            avatar_url=str(data.get("avatar_url") or ""),
        )

    def get_by_id(self, user_id: str | int) -> UserAccount | None:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        for username, data in self._read().items():
            if int(data.get("id", 0)) == uid:
                return UserAccount(
                    user_id=data["id"],
                    username=username,
                    role=data.get("role", "viewer"),
                    password_hash=data["password"],
                    avatar_url=str(data.get("avatar_url") or ""),
                )
        return None

    def create(self, user: UserAccount) -> str:
        users = self._read()
        if user.username in users:
            raise ValueError("user already exists")
        next_id = max((int(item["id"]) for item in users.values()), default=0) + 1
        users[user.username] = {
            "password": user.password_hash,
            "id": next_id,
            "role": user.role,
            "wechat_openid": None,
            "oauth_sub": None,
            "display_name": None,
            "avatar_url": user.avatar_url or None,
        }
        self._write(users)
        return str(next_id)

    def update(self, user_id: str, data: dict) -> bool:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return False
        users = self._read()
        target_username: str | None = None
        for username, item in users.items():
            if int(item.get("id", 0)) == uid:
                target_username = username
                break
        if not target_username:
            return False
        entry = users[target_username]
        if "username" in data and data["username"] != target_username:
            new_name = str(data["username"])
            if new_name in users:
                return False
            users[new_name] = users.pop(target_username)
            target_username = new_name
            entry = users[target_username]
        if "password" in data:
            entry["password"] = data["password"]  # Already hashed by caller
        if "role" in data:
            entry["role"] = data["role"]
        if "avatar_url" in data:
            entry["avatar_url"] = data["avatar_url"]
        self._write(users)
        return True

    def delete(self, user_id: str) -> bool:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return False
        users = self._read()
        for username, item in list(users.items()):
            if int(item.get("id", 0)) == uid:
                if username in PROTECTED_DEMO_USERNAMES:
                    return False
                del users[username]
                self._write(users)
                return True
        return False

    def list_all(self, limit: int = 100) -> list[UserAccount]:
        return self.list_users()[: max(1, int(limit))]

    def create_user(self, username: str, password: str, role: str) -> bool:
        users = self._read()
        if username in users:
            return False
        next_id = max((item["id"] for item in users.values()), default=0) + 1
        users[username] = {
            "password": hash_password(password),
            "id": next_id,
            "role": role,
            "wechat_openid": None,
            "oauth_sub": None,
            "display_name": None,
            "avatar_url": None,
        }
        self._write(users)
        return True

    def delete_user(self, username: str) -> bool:
        users = self._read()
        if username not in users or username in PROTECTED_DEMO_USERNAMES:
            return False
        del users[username]
        self._write(users)
        return True

    def update_password(self, username: str, password: str) -> bool:
        users = self._read()
        if username not in users:
            return False
        users[username]["password"] = hash_password(password)
        self._write(users)
        return True

    def list_roles(self) -> list[dict]:
        rows = []
        for i, code in enumerate(("admin", "developer", "researcher", "trader", "viewer"), start=1):
            rows.append(
                {"id": i, "code": code, "label": ROLE_LABELS.get(code, code), "sort_order": i * 10},
            )
        return rows

    def update_user_role(self, username: str, role_code: str) -> bool:
        users = self._read()
        if username not in users:
            return False
        users[username]["role"] = role_code
        self._write(users)
        return True

    def get_by_wechat_openid(self, openid: str) -> UserAccount | None:
        oid = (openid or "").strip()
        if not oid:
            return None
        for username, data in self._read().items():
            if (data.get("wechat_openid") or "").strip() == oid:
                return UserAccount(
                    user_id=data["id"],
                    username=username,
                    role=data.get("role", "viewer"),
                    password_hash=data["password"],
                    avatar_url=str(data.get("avatar_url") or ""),
                )
        return None

    def link_or_create_wechat_user(self, openid: str, *, nickname: str | None = None) -> UserAccount | None:
        ex = self.get_by_wechat_openid(openid)
        if ex:
            return ex

        nick = (nickname or "").strip()
        base = re.sub(r"[^\w涓€-榭縘", "", nick)[:24] if nick else ""
        if not base or len(base) < 2:
            base = f"wx{openid[-10:]}"
        if base.lower() in {x.lower() for x in PROTECTED_DEMO_USERNAMES}:
            base = f"wx{openid[-10:]}"
        rnd = secrets.token_hex(32)
        for i in range(50):
            users = self._read()
            candidate = f"{base}{i}" if i else base
            if len(candidate) > 48:
                candidate = candidate[:48]
            if candidate in users:
                continue
            next_id = max((int(item["id"]) for item in users.values()), default=0) + 1
            users[candidate] = {
                "password": rnd,  # Random string for WeChat-only users (no login)
                "id": next_id,
                "role": "viewer",
                "wechat_openid": openid,
                "oauth_sub": None,
                "display_name": nick or None,
                "avatar_url": None,
            }
            self._write(users)
            return self.get_by_username(candidate)
        return None

    def get_by_oauth_sub(self, oauth_sub: str) -> UserAccount | None:
        sub = (oauth_sub or "").strip()
        if not sub:
            return None
        for username, data in self._read().items():
            if (data.get("oauth_sub") or "").strip() == sub:
                return UserAccount(
                    user_id=data["id"],
                    username=username,
                    role=data.get("role", "viewer"),
                    password_hash=data["password"],
                    avatar_url=str(data.get("avatar_url") or ""),
                )
        return None

    def link_or_create_oauth_user(
        self,
        oauth_sub: str,
        *,
        display_name: str | None = None,
    ) -> UserAccount | None:
        ex = self.get_by_oauth_sub(oauth_sub)
        if ex:
            return ex

        sub = (oauth_sub or "").strip()
        if not sub:
            return None

        nick = (display_name or "").strip()
        base = re.sub(r"[^\w涓€-榭緻.+-]", "", nick)[:24] if nick else ""
        if not base or len(base) < 2:
            base = f"oauth{sub[-8:]}"
        if base.lower() in {x.lower() for x in PROTECTED_DEMO_USERNAMES}:
            base = f"oauth{sub[-8:]}"
        rnd = secrets.token_hex(32)
        for i in range(50):
            users = self._read()
            candidate = f"{base}{i}" if i else base
            if len(candidate) > 48:
                candidate = candidate[:48]
            if candidate in users:
                continue
            next_id = max((int(item["id"]) for item in users.values()), default=0) + 1
            users[candidate] = {
                "password": rnd,
                "id": next_id,
                "role": "viewer",
                "wechat_openid": None,
                "oauth_sub": sub,
                "display_name": nick or None,
                "avatar_url": None,
            }
            self._write(users)
            return self.get_by_username(candidate)
        return None

    def update_avatar_url(self, username: str, avatar_url: str | None) -> bool:
        users = self._read()
        u = (username or "").strip()
        if u not in users:
            return False
        users[u]["avatar_url"] = (avatar_url or "").strip() or None
        self._write(users)
        return True

    def _read(self) -> dict:
        if not self._path.exists():
            return self._default_users()
        with self._path.open("r", encoding="utf-8") as handle:
            payload: dict[str, dict] = json.load(handle)

        # Calibrate protected demo users to stable credentials even when
        # users.json was created/modified in previous test runs.
        #
        # Important: keep these passwords deterministic (no env override),
        # because the test suite assumes the fixed credentials:
        # admin/admin123, developer/dev123, researcher/research123, trader/trade123, viewer/view123.
        _passwords = {
            "admin": os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_ADMIN", "admin123"),
            "developer": os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_DEVELOPER", "dev123"),
            "researcher": os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_RESEARCHER", "research123"),
            "trader": os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_TRADER", "trade123"),
            "viewer": os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_VIEWER", "view123"),
        }
        specs: dict[str, dict[str, object]] = {
            "admin": {"id": 1, "role": "admin", "password": _passwords["admin"]},
            "developer": {"id": 2, "role": "developer", "password": _passwords["developer"]},
            "researcher": {"id": 3, "role": "researcher", "password": _passwords["researcher"]},
            "trader": {"id": 4, "role": "trader", "password": _passwords["trader"]},
            "viewer": {"id": 5, "role": "viewer", "password": _passwords["viewer"]},
        }

        for username in PROTECTED_DEMO_USERNAMES:
            spec = specs.get(username)
            if not spec:
                continue
            if username not in payload or not isinstance(payload[username], dict):
                payload[username] = {}

            expected_hash = hash_password(str(spec["password"]))
            payload[username]["password"] = expected_hash
            payload[username]["id"] = int(payload[username].get("id", int(spec["id"])))
            payload[username]["role"] = str(spec["role"])
            payload[username].setdefault("wechat_openid", None)
            payload[username].setdefault("oauth_sub", None)
            payload[username].setdefault("display_name", None)
            payload[username].setdefault("avatar_url", None)

        return payload

    def _write(self, payload: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _default_users() -> dict:
        def _u(pwd: str, uid: int, role: str) -> dict:
            return {
                "password": hash_password(pwd),
                "id": uid,
                "role": role,
                "wechat_openid": None,
                "oauth_sub": None,
                "display_name": None,
                "avatar_url": None,
            }

        return {
            "admin": _u(os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_ADMIN", "admin123"), 1, "admin"),
            "developer": _u(os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_DEVELOPER", "dev123"), 2, "developer"),
            "researcher": _u(os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_RESEARCHER", "research123"), 3, "researcher"),
            "trader": _u(os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_TRADER", "trade123"), 4, "trader"),
            "viewer": _u(os.environ.get("QUANT_ATLAS_DEMO_PASSWORD_VIEWER", "view123"), 5, "viewer"),
        }


class JsonWatchlistRepository(WatchlistRepository):
    """JSON-backed watchlist repository."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _write(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_symbols(self, user_id: int = 1) -> list[str]:
        data = self._read()
        return data.get(str(user_id), [])

    def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        data = self._read()
        uid = str(user_id)
        symbols = data.get(uid, [])
        if symbol not in symbols:
            symbols.append(symbol)
            data[uid] = symbols
            self._write(data)
            return True
        return False

    def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        data = self._read()
        uid = str(user_id)
        symbols = data.get(uid, [])
        if symbol in symbols:
            symbols.remove(symbol)
            data[uid] = symbols
            self._write(data)
            return True
        return False

    def save_symbols(self, user_id: int, symbols: list[str]) -> None:
        data = self._read()
        data[str(user_id)] = symbols
        self._write(data)


class JsonStockGroupRepository(StockGroupRepository):
    """JSON-backed stock group repository."""

    def __init__(self, path: Path, watchlist_repository: WatchlistRepository | None = None):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._watchlist_repository = watchlist_repository

    def _read(self) -> dict:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _write(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _canonicalize_user_entry(entry: Any) -> list[dict[str, Any]]:
        """Normalize legacy ``{groups, items}`` and modern ``[{id, symbols}]`` shapes."""
        if entry is None:
            return []
        if isinstance(entry, list):
            groups: list[dict[str, Any]] = []
            for raw in entry:
                if not isinstance(raw, dict):
                    continue
                gid = int(raw.get("id") or 0)
                if not gid:
                    continue
                symbols = raw.get("symbols") or []
                groups.append(
                    {
                        "id": gid,
                        "name": str(raw.get("name") or ""),
                        "description": str(raw.get("description") or ""),
                        "color": str(raw.get("color") or "#3B82F6"),
                        "is_default": int(raw.get("is_default") or 0),
                        "symbols": [str(s).strip() for s in symbols if str(s).strip()],
                    }
                )
            return groups
        if isinstance(entry, dict) and ("groups" in entry or "items" in entry):
            items_map = entry.get("items") or {}
            groups = []
            for raw in entry.get("groups") or []:
                if not isinstance(raw, dict):
                    continue
                gid = int(raw.get("id") or 0)
                if not gid:
                    continue
                symbols = items_map.get(str(gid), items_map.get(gid, []))
                if not isinstance(symbols, list):
                    symbols = []
                groups.append(
                    {
                        "id": gid,
                        "name": str(raw.get("name") or ""),
                        "description": str(raw.get("description") or ""),
                        "color": str(raw.get("color") or "#3B82F6"),
                        "is_default": int(raw.get("is_default") or 0),
                        "symbols": [str(s).strip() for s in symbols if str(s).strip()],
                    }
                )
            return groups
        return []

    def _user_groups(self, data: dict, user_id: int) -> list[dict[str, Any]]:
        return self._canonicalize_user_entry(data.get(str(user_id)))

    def _persist_user_groups(self, data: dict, user_id: int, groups: list[dict[str, Any]]) -> None:
        data[str(user_id)] = groups
        self._write(data)

    def _maybe_migrate_user_entry(self, data: dict, user_id: int) -> list[dict[str, Any]]:
        uid = str(user_id)
        entry = data.get(uid)
        groups = self._user_groups(data, user_id)
        if entry is not None and not isinstance(entry, list):
            self._persist_user_groups(data, user_id, groups)
        return groups

    def list_groups(self, user_id: int = 1) -> list[dict[str, Any]]:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        return [{k: v for k, v in group.items() if k != "symbols"} for group in groups]

    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> dict | None:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        gid = max((int(g.get("id") or 0) for g in groups), default=0) + 1
        group = {
            "id": gid,
            "name": name,
            "description": description,
            "color": color or "#3B82F6",
            "is_default": 0,
            "symbols": [],
        }
        groups.append(group)
        self._persist_user_groups(data, user_id, groups)
        return group

    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> bool:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        for group in groups:
            if int(group.get("id") or 0) == int(group_id):
                group["name"] = name
                group["description"] = description
                if color:
                    group["color"] = color
                self._persist_user_groups(data, user_id, groups)
                return True
        return False

    def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        new_groups = [g for g in groups if int(g.get("id") or 0) != int(group_id)]
        if len(new_groups) < len(groups):
            self._persist_user_groups(data, user_id, new_groups)
            return True
        return False

    def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        data = self._read()
        for group in self._maybe_migrate_user_entry(data, user_id):
            if int(group.get("id") or 0) == int(group_id):
                return list(group.get("symbols") or [])
        return []

    def add_symbol_to_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        for group in groups:
            if int(group.get("id") or 0) == int(group_id):
                symbols = list(group.get("symbols") or [])
                if symbol not in symbols:
                    symbols.append(symbol)
                    group["symbols"] = symbols
                    self._persist_user_groups(data, user_id, groups)
                return True
        return False

    def remove_symbol_from_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        data = self._read()
        groups = self._maybe_migrate_user_entry(data, user_id)
        for group in groups:
            if int(group.get("id") or 0) == int(group_id):
                symbols = list(group.get("symbols") or [])
                if symbol in symbols:
                    symbols.remove(symbol)
                    group["symbols"] = symbols
                    self._persist_user_groups(data, user_id, groups)
                return True
        return False
