from __future__ import annotations
"""SQLite-backed repositories."""


import json
import sqlite3
from pathlib import Path

from ....core.password_hash import hash_password

import logging
logger = logging.getLogger(__name__)
_ROLE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, "admin", "管理员", 10),
    (2, "developer", "开发者", 20),
    (3, "researcher", "研究员", 30),
    (4, "trader", "交易员", 40),
    (5, "viewer", "访客", 50),
)


class SQLiteRepositoryBase:
    """Shared SQLite initialization and helpers."""

    def __init__(
        self,
        db_path: Path,
        users_json_path: Path | None = None,
        watchlist_json_path: Path | None = None,
        stock_groups_json_path: Path | None = None,
    ):
        self._db_path = db_path
        self._users_json_path = users_json_path
        self._watchlist_json_path = watchlist_json_path
        self._stock_groups_json_path = stock_groups_json_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA temp_store=MEMORY;
            PRAGMA foreign_keys=ON;
            """
        )
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS stock_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    is_default INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS stock_group_items (
                    group_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_removed INTEGER DEFAULT 0,
                    PRIMARY KEY (group_id, symbol),
                    FOREIGN KEY (group_id) REFERENCES stock_groups(id) ON DELETE CASCADE
                );
                """
            )
            try:
                with self._connect() as conn:
                    conn.execute("ALTER TABLE stock_group_items ADD COLUMN added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception as e:
                logger.warning("sqlite_repositories.py._init_db: %s", e)
            try:
                with self._connect() as conn:
                    conn.execute("ALTER TABLE stock_group_items ADD COLUMN is_removed INTEGER DEFAULT 0")
            except Exception as e:
                logger.warning("sqlite_repositories.py._init_db: %s", e)

            self._ensure_roles_and_user_schema(conn)
            self._seed_users(conn)
            self._seed_groups(conn)
            self._seed_watchlist(conn)

    def _seed_users(self, conn: sqlite3.Connection) -> None:
        existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        import os
        specs = (
            (1, "admin", os.environ.get("SEED_USER_PASSWORD_ADMIN", "admin123"), "admin", 1),
            (2, "developer", os.environ.get("SEED_USER_PASSWORD_DEV", "dev123"), "developer", 2),
            (3, "researcher", os.environ.get("SEED_USER_PASSWORD_RESEARCHER", "research123"), "researcher", 3),
            (4, "trader", os.environ.get("SEED_USER_PASSWORD_TRADER", "trade123"), "trader", 4),
            (5, "viewer", os.environ.get("SEED_USER_PASSWORD_VIEWER", "view123"), "viewer", 5),
        )

        if existing:
            # Make demo credentials deterministic for tests even if the
            # sqlite DB file already exists with legacy hashes.
            for uid, uname, pwd, role_code, rid in specs:
                expected_hash = hash_password(pwd)
                row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (uname,)).fetchone()
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO users(id, username, password_hash, role, role_id, wechat_openid, display_name)
                        VALUES (?, ?, ?, ?, ?, NULL, NULL)
                        """,
                        (uid, uname, expected_hash, role_code, rid),
                    )
                elif str(row["password_hash"]) != expected_hash:
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE username = ?",
                        (expected_hash, uname),
                    )
            return

        payload = self._read_json(self._users_json_path) if self._users_json_path else None
        if not payload:
            for uid, uname, pwd, role_code, rid in specs:
                conn.execute(
                    """
                    INSERT INTO users(id, username, password_hash, role, role_id, wechat_openid, display_name)
                    VALUES (?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (uid, uname, hash_password(pwd), role_code, rid),
                )
            return
        for username, data in payload.items():
            role_code = str(data.get("role", "viewer"))
            row = conn.execute("SELECT id FROM roles WHERE code = ? LIMIT 1", (role_code,)).fetchone()
            rid = row["id"] if row else 5
            conn.execute(
                """
                INSERT INTO users(id, username, password_hash, role, role_id, wechat_openid, display_name)
                VALUES (?, ?, ?, ?, ?, NULL, NULL)
                """,
                (data["id"], username, data["password"], role_code, rid),
            )

    def _seed_groups(self, conn: sqlite3.Connection) -> None:
        existing = conn.execute("SELECT COUNT(*) AS count FROM stock_groups").fetchone()["count"]
        if existing:
            return
        payload = self._read_json(self._stock_groups_json_path) if self._stock_groups_json_path else None
        groups = (payload or {}).get("groups", [])
        items = (payload or {}).get("items", {})

        if not groups:
            conn.execute(
                "INSERT INTO stock_groups(name, description, is_default) VALUES (?, ?, 1)",
                ("自选股", "默认分组"),
            )
            return

        id_map: dict[int, int] = {}
        for group in groups:
            cursor = conn.execute(
                "INSERT INTO stock_groups(name, description, is_default) VALUES (?, ?, ?)",
                (
                    group.get("name", ""),
                    group.get("description", ""),
                    int(group.get("is_default", 0)),
                ),
            )
            id_map[int(group["id"])] = cursor.lastrowid

        for old_group_id, symbols in items.items():
            new_group_id = id_map.get(int(old_group_id))
            if not new_group_id:
                continue
            from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
            for symbol in symbols:
                normalized = SymbolNormalizer.to_db_code(str(symbol))
                conn.execute(
                    "INSERT OR IGNORE INTO stock_group_items(group_id, symbol) VALUES (?, ?)",
                    (new_group_id, normalized),
                )

    def _seed_watchlist(self, conn: sqlite3.Connection) -> None:
        existing = conn.execute("SELECT COUNT(*) AS count FROM watchlist").fetchone()["count"]
        if existing:
            return
        payload = self._read_json(self._watchlist_json_path) if self._watchlist_json_path else []
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        normalized = [SymbolNormalizer.to_db_code(str(item)) for item in (payload or [])]
        for symbol in normalized:
            conn.execute("INSERT OR IGNORE INTO watchlist(symbol) VALUES (?)", (symbol,))
        default_group = conn.execute(
            "SELECT id FROM stock_groups WHERE is_default = 1 ORDER BY id LIMIT 1"
        ).fetchone()
        if default_group:
            for symbol in normalized:
                conn.execute(
                    "INSERT OR IGNORE INTO stock_group_items(group_id, symbol) VALUES (?, ?)",
                    (default_group["id"], symbol),
                )

    @staticmethod
    def _read_json(path: Path | None):
        if not path or not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _ensure_roles_and_user_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        for rid, code, label, sort_order in _ROLE_ROWS:
            conn.execute(
                "INSERT OR IGNORE INTO roles(id, code, label, sort_order) VALUES (?, ?, ?, ?)",
                (rid, code, label, sort_order),
            )

        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "role_id" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id)")
        if "wechat_openid" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN wechat_openid TEXT")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_wechat_openid "
            "ON users(wechat_openid) WHERE wechat_openid IS NOT NULL AND length(trim(wechat_openid)) > 0"
        )
        if "display_name" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        cols2 = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "avatar_url" not in cols2:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

        conn.execute(
            """
            UPDATE users SET role_id = (
                SELECT id FROM roles WHERE roles.code = users.role COLLATE NOCASE LIMIT 1
            )
            WHERE role_id IS NULL AND EXISTS (SELECT 1 FROM roles WHERE roles.code = users.role COLLATE NOCASE)
            """
        )
        viewer_id = conn.execute("SELECT id FROM roles WHERE code = 'viewer' LIMIT 1").fetchone()
        conn.execute(
            "UPDATE users SET role_id = ? WHERE role_id IS NULL", (viewer_id["id"],) if viewer_id else ()
        )

    def _ensure_roles_and_watchlist(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS watchlist ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL DEFAULT 1, "
            "symbol TEXT NOT NULL, "
            "UNIQUE(user_id, symbol)"
            ")"
        )
