"""SQLite implementation for BasicMarketDataRepository."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ....config import INSTANCE_DIR

LOCK = threading.Lock()


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class SQLiteBasicMarketDataRepository:
    """SQLite implementation of BasicMarketDataRepository."""

    def __init__(self, db_path: Path | None = None, *, mysql: Any = None, session_factory: Any = None, **kwargs) -> None:
        self._path = Path(db_path or (INSTANCE_DIR / "basic_market_data.db"))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect_sqlite(self):
        conn = sqlite3.connect(str(self._path), timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with LOCK:
            with self._connect_sqlite() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS longhu_daily (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_date TEXT NOT NULL,
                        code TEXT NOT NULL,
                        name TEXT,
                        reason TEXT,
                        raw_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(trade_date, code)
                    );
                    CREATE TABLE IF NOT EXISTS yanbao_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        title TEXT,
                        stock_code TEXT,
                        org_name TEXT,
                        pub_date TEXT,
                        report_url TEXT,
                        raw_json TEXT NOT NULL,
                        crawl_batch TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS basic_data_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS cn_financial_stash (
                        code TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                conn.commit()

    def replace_longhu_day(self, trade_date: str, rows: list[dict[str, Any]]) -> int:
        td = trade_date.strip()[:10]
        now = _utc_ts()
        with LOCK:
            with self._connect_sqlite() as conn:
                conn.execute("DELETE FROM longhu_daily WHERE trade_date=?", (td,))
                for r in rows:
                    code = str(r.get("code") or "").strip()[-6:].zfill(6)
                    if not code.isdigit():
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO longhu_daily
                        (trade_date, code, name, reason, raw_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            td,
                            code,
                            str(r.get("name") or "")[:64],
                            str(r.get("reason") or "")[:512],
                            json.dumps(r.get("raw") or r, ensure_ascii=False),
                            now,
                        ),
                    )
                conn.commit()
        return len(rows)

    def list_longhu_by_date(
        self,
        trade_date: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        td = trade_date.strip()[:10]
        off = max(0, int(offset))
        lim = max(1, int(limit))
        with self._connect_sqlite() as conn:
            rows = conn.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE trade_date=?
                ORDER BY code
                LIMIT ? OFFSET ?
                """,
                (td, lim, off),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out

    def count_longhu_by_date(self, trade_date: str) -> int:
        td = trade_date.strip()[:10]
        with self._connect_sqlite() as conn:
            row = conn.execute(
                "SELECT COUNT(1) AS n FROM longhu_daily WHERE trade_date=?",
                (td,),
            ).fetchone()
            return int(row["n"] if row else 0)

    def set_meta(self, key: str, value: str) -> None:
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO basic_data_meta (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, _utc_ts()),
            )
            conn.commit()

    def get_meta(self, key: str) -> str | None:
        with self._connect_sqlite() as conn:
            row = conn.execute("SELECT value FROM basic_data_meta WHERE key=?", (key,)).fetchone()
            return str(row["value"]) if row else None

    def upsert_financial_stash(self, code: str, payload: dict[str, Any]) -> None:
        c = str(code).strip()[-6:].zfill(6)
        if len(c) != 6 or not c.isdigit():
            return
        now = _utc_ts()
        blob = json.dumps(payload, ensure_ascii=False)
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cn_financial_stash (code, payload_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (c, blob, now),
            )
            conn.commit()

    def insert_yanbao_batch(self, category: str, items: list[dict[str, Any]], batch_id: str) -> int:
        now = _utc_ts()
        with self._connect_sqlite() as conn:
            for it in items:
                conn.execute(
                    """
                    INSERT INTO yanbao_items
                    (category, title, stock_code, org_name, pub_date, report_url, raw_json, crawl_batch, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        category[:64],
                        str(it.get("title") or "")[:512],
                        (str(it.get("stock_code") or "")[:16] or None),
                        str(it.get("org_name") or "")[:128],
                        str(it.get("pub_date") or "")[:32],
                        str(it.get("report_url") or "")[:1024],
                        json.dumps(it.get("raw") or it, ensure_ascii=False),
                        batch_id[:32],
                        now,
                    ),
                )
            conn.commit()
        return len(items)

    def upsert_longhu_rows(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        grouped: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            td = str(r.get("trade_date") or "")[:10]
            if not td:
                continue
            grouped.setdefault(td, []).append(r)
        total = 0
        for td, sub in grouped.items():
            total += self.replace_longhu_day(td, sub)
        return total

    def count_longhu_rows(self) -> int:
        with self._connect_sqlite() as conn:
            row = conn.execute("SELECT COUNT(1) AS n FROM longhu_daily").fetchone()
            return int(row["n"] if row else 0)

    def latest_longhu_trade_date(self) -> str | None:
        with self._connect_sqlite() as conn:
            row = conn.execute("SELECT MAX(trade_date) AS d FROM longhu_daily").fetchone()
            return str(row["d"])[:10] if row and row["d"] else None

    def list_longhu_latest_dates(self, limit: int = 20) -> list[str]:
        with self._connect_sqlite() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT trade_date
                FROM longhu_daily
                ORDER BY trade_date DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            return [str(row["trade_date"])[:10] for row in rows]

    def list_longhu_for_code(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        c = str(code or "").strip()[-6:].zfill(6)
        with self._connect_sqlite() as conn:
            rows = conn.execute(
                """
                SELECT trade_date, code, name, reason, raw_json, updated_at
                FROM longhu_daily
                WHERE code=?
                ORDER BY trade_date DESC
                LIMIT ?
                """,
                (c, int(limit)),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "trade_date": str(r["trade_date"]),
                        "code": str(r["code"]),
                        "name": str(r["name"] or ""),
                        "reason": str(r["reason"] or ""),
                        "detail": raw,
                        "updated_at": str(r["updated_at"] or ""),
                    }
                )
            return out

    def list_yanbao(self, *, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 1000))
        with self._connect_sqlite() as conn:
            if category:
                rows = conn.execute(
                    """
                    SELECT * FROM yanbao_items
                    WHERE category=?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (category, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM yanbao_items ORDER BY id DESC LIMIT ?",
                    (lim,),
                ).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    raw = json.loads(str(r["raw_json"] or "{}"))
                except Exception:
                    raw = {}
                out.append(
                    {
                        "id": int(r["id"]),
                        "category": str(r["category"] or ""),
                        "title": str(r["title"] or ""),
                        "stock_code": str(r["stock_code"] or ""),
                        "org_name": str(r["org_name"] or ""),
                        "pub_date": str(r["pub_date"] or ""),
                        "report_url": str(r["report_url"] or ""),
                        "raw": raw,
                        "crawl_batch": str(r["crawl_batch"] or ""),
                        "created_at": str(r["created_at"] or ""),
                    }
                )
            return out

    def count_financial_stash_rows(self) -> int:
        with self._connect_sqlite() as conn:
            row = conn.execute("SELECT COUNT(1) AS n FROM cn_financial_stash").fetchone()
            return int(row["n"] if row else 0)
