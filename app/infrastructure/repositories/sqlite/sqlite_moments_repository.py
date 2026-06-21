"""SQLite implementation for MomentsRepository."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from ....core.shanghai_time import now_sh_str


class SQLiteMomentsRepository:
    """SQLite implementation of MomentsRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_sqlite(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS moments_posts (
                  post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  actor_type TEXT NOT NULL,
                  actor_id TEXT NOT NULL,
                  author_name TEXT NOT NULL,
                  content_text TEXT NOT NULL,
                  content_json TEXT,
                  market_date TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS moment_attachments (
                  attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  media_type TEXT NOT NULL,
                  file_name TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  file_url TEXT NOT NULL,
                  mime_type TEXT,
                  size_bytes INTEGER DEFAULT 0,
                  meta_json TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS moment_likes (
                  like_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  user_id TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(post_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS moment_comments (
                  comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  user_id TEXT NOT NULL,
                  content_text TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def create_post(self, *, actor_type: str, actor_id: str, author_name: str, content_text: str, content: dict[str, Any] | None = None, market_date: str | None = None) -> int:
        now = now_sh_str()
        payload_json = json.dumps(content or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO moments_posts (actor_type, actor_id, author_name, content_text, content_json, market_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (actor_type, actor_id, author_name, content_text, payload_json, market_date[:10] if market_date else None, now)
            )
            conn.commit()
            return cur.lastrowid or 0

    def add_attachment(self, *, post_id: int, media_type: str, file_name: str, file_path: str, file_url: str, mime_type: str | None, size_bytes: int, meta: dict[str, Any] | None = None) -> int:
        now = now_sh_str()
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO moment_attachments (post_id, media_type, file_name, file_path, file_url, mime_type, size_bytes, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (post_id, media_type, file_name, file_path, file_url, mime_type or "", int(size_bytes or 0), meta_json, now)
            )
            conn.commit()
            return cur.lastrowid or 0

    def list_feed(self, *, limit: int = 50, before_post_id: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if before_post_id:
                cur = conn.execute(
                    "SELECT * FROM moments_posts WHERE post_id < ? ORDER BY post_id DESC LIMIT ?",
                    (before_post_id, limit)
                )
            else:
                cur = conn.execute("SELECT * FROM moments_posts ORDER BY post_id DESC LIMIT ?", (limit,))
            posts = cur.fetchall()
            res = []
            for p in posts:
                d = dict(p)
                d["attachments"] = []
                cur2 = conn.execute("SELECT COUNT(*) as cnt FROM moment_likes WHERE post_id = ?", (p["post_id"],))
                d["like_count"] = cur2.fetchone()["cnt"]
                cur3 = conn.execute("SELECT COUNT(*) as cnt FROM moment_comments WHERE post_id = ?", (p["post_id"],))
                d["comment_count"] = cur3.fetchone()["cnt"]
                res.append(d)
            return res

    def toggle_like(self, *, post_id: int, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT like_id FROM moment_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM moment_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
                liked = False
            else:
                cur.execute(
                    "INSERT INTO moment_likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
                    (post_id, user_id, now_sh_str())
                )
                liked = True
            conn.commit()
            cur.execute("SELECT COUNT(*) as cnt FROM moment_likes WHERE post_id = ?", (post_id,))
            cnt = cur.fetchone()["cnt"]
            return {"ok": True, "liked": liked, "like_count": cnt}
