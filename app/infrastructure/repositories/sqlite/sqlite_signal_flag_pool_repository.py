"""SQLite implementation for SignalFlagPoolRepository."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class SQLiteSignalFlagPoolRepository:
    """SQLite implementation of SignalFlagPoolRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path or ".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=60)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_flag_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pool_date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    price REAL,
                    change_pct REAL,
                    volume REAL,
                    amount REAL,
                    turnover REAL,
                    source TEXT,
                    industry TEXT,
                    pe REAL,
                    pb REAL,
                    signal_strategies TEXT NOT NULL DEFAULT '[]',
                    signal_strategies_sell TEXT NOT NULL DEFAULT '[]',
                    long_horizon TEXT NOT NULL DEFAULT '{}',
                    mid_horizon TEXT NOT NULL DEFAULT '{}',
                    short_horizon TEXT NOT NULL DEFAULT '{}',
                    safety_score REAL NOT NULL DEFAULT 0,
                    extra_snapshot TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(pool_date, code)
                )
                """
            )
            c.commit()

    def list_dates(self, *, limit: int = 120) -> list[str]:
        with self._connect() as c:
            cur = c.execute(
                """
                SELECT pool_date FROM signal_flag_pool
                GROUP BY pool_date
                ORDER BY pool_date DESC
                LIMIT ?
                """,
                (int(limit),)
            )
            return [str(r["pool_date"])[:10] for r in cur.fetchall()]

    def get_pool(self, pool_date: str) -> list[dict[str, Any]]:
        d = (pool_date or "")[:10]
        with self._connect() as c:
            cur = c.execute(
                """
                SELECT * FROM signal_flag_pool
                WHERE pool_date = ?
                ORDER BY amount DESC, code ASC
                """,
                (d,)
            )
            out = []
            for r in cur.fetchall():
                item = dict(r)
                for k in ("signal_strategies", "signal_strategies_sell", "long_horizon", "mid_horizon", "short_horizon", "extra_snapshot"):
                    if k in item and isinstance(item[k], str):
                        try:
                            item[k] = json.loads(item[k])
                        except json.JSONDecodeError:
                            item[k] = [] if "strategies" in k else {}
                out.append(item)
            return out

    def replace_pool(self, pool_date: str, rows: list[dict[str, Any]]) -> int:
        d = (pool_date or "")[:10]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        def _json(v, fallback):
            return json.dumps(v or fallback, ensure_ascii=False)
        batch = []
        for r in rows:
            batch.append((
                d,
                str(r.get("code") or ""),
                str(r.get("name") or ""),
                float(r.get("price") or 0),
                float(r.get("change_pct") or 0),
                float(r.get("volume") or 0),
                float(r.get("amount") or 0),
                float(r.get("turnover") or 0),
                str(r.get("source") or ""),
                str(r.get("industry") or ""),
                float(r.get("pe") or 0),
                float(r.get("pb") or 0),
                _json(r.get("signal_strategies"), []),
                _json(r.get("signal_strategies_sell"), []),
                _json(r.get("long_horizon"), {}),
                _json(r.get("mid_horizon"), {}),
                _json(r.get("short_horizon"), {}),
                float(r.get("safety_score") or 0),
                _json(r.get("extra_snapshot"), {}),
                now,
            ))
        with self._connect() as c:
            c.execute("DELETE FROM signal_flag_pool WHERE pool_date = ?", (d,))
            c.executemany(
                """INSERT INTO signal_flag_pool (pool_date,code,name,price,change_pct,volume,amount,
                   turnover,source,industry,pe,pb,signal_strategies,signal_strategies_sell,
                   long_horizon,mid_horizon,short_horizon,safety_score,extra_snapshot,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                batch,
            )
            c.commit()
        return len(rows)
