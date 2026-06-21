"""SQLite implementation for NewsArchiveRepository."""

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_hash(market: str, symbol: str, scope: str, title: str, published_at: str, url: str) -> str:
    raw = f"{market}|{symbol}|{scope}|{title}|{published_at}|{url}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


class SQLiteNewsArchiveRepository:
    """SQLite implementation of NewsArchiveRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS archived_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    url TEXT NOT NULL,
                    source TEXT,
                    published_at TEXT,
                    content_hash TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    UNIQUE(market, symbol, scope, content_hash)
                );
                CREATE TABLE IF NOT EXISTS news_symbol_meta (
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    company_name TEXT,
                    industry_hint TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (market, symbol)
                );
                """
            )
            conn.commit()

    def latest_fetched_at(self, market: str, symbol: str) -> str | None:
        m = market.upper()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(fetched_at) AS ts FROM archived_news WHERE market = ? AND symbol = ?",
                (m, symbol),
            ).fetchone()
            return str(row["ts"]) if row and row["ts"] else None

    def get_meta(self, market: str, symbol: str) -> dict[str, Any]:
        m = market.upper()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT company_name, industry_hint, updated_at FROM news_symbol_meta "
                "WHERE market = ? AND symbol = ?",
                (m, symbol),
            ).fetchone()
            return dict(row) if row else {}

    def upsert_meta(self, market: str, symbol: str, *, company_name: str, industry_hint: str) -> None:
        m = market.upper()
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_symbol_meta (market, symbol, company_name, industry_hint, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(market, symbol) DO UPDATE SET
                    company_name=excluded.company_name,
                    industry_hint=excluded.industry_hint,
                    updated_at=excluded.updated_at
                """,
                (m, symbol, company_name, industry_hint, now),
            )
            conn.commit()

    def ingest_snapshot(self, market: str, symbol: str, snapshot: dict[str, Any]) -> int:
        m = market.upper()
        sym = symbol
        self.upsert_meta(m, sym, company_name=str(snapshot.get("company_name_hint") or ""), industry_hint=str(snapshot.get("industry_hint") or ""))
        now = _utc_now()
        inserted = 0

        with self._connect() as conn:
            for scope, key in ("symbol", "news"), ("industry", "industry_news"):
                for item in snapshot.get(key) or []:
                    title = str(item.get("title") or "")
                    url = str(item.get("url") or "")
                    if not title and not url: continue
                    ch = _row_hash(m, sym, scope, title, str(item.get("published_at") or ""), url)

                    existing = conn.execute(
                        "SELECT 1 FROM archived_news WHERE market = ? AND symbol = ? AND scope = ? AND content_hash = ?",
                        (m, sym, scope, ch)
                    ).fetchone()
                    if existing: continue

                    conn.execute(
                        """
                        INSERT INTO archived_news (market, symbol, scope, title, summary, url, source, published_at, content_hash, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            m, sym, scope, title,
                            str(item.get("summary") or ""),
                            url or f"urn:empty:{ch[:16]}",
                            str(item.get("source") or ""),
                            str(item.get("published_at") or ""),
                            ch, now
                        )
                    )
                    inserted += 1
            conn.commit()
        return inserted

    def list_for_symbol(self, market: str, symbol: str, *, limit: int = 80) -> list[dict[str, Any]]:
        m = market.upper()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT title, summary, url, source, published_at, fetched_at, scope
                FROM archived_news
                WHERE market = ? AND symbol = ?
                ORDER BY fetched_at DESC, published_at DESC
                LIMIT ?
                """,
                (m, symbol, limit)
            ).fetchall()
            return [{
                "title": r["title"], "summary": r["summary"] or "", "url": r["url"],
                "source": r["source"] or "", "published_at": r["published_at"] or "",
                "fetched_at": r["fetched_at"] or "", "news_scope": r["scope"]
            } for r in rows]
