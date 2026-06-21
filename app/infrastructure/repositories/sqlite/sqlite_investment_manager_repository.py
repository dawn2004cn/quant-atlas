"""SQLite implementation for InvestmentManagerRepository."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ManagerRow:
    manager_id: str
    strategy_id: str
    name: str
    bio: str
    cohort: str
    deployed_at: str | None
    active: int
    tagline: str = ""
    specialty: str = ""


class SQLiteInvestmentManagerRepository:
    """SQLite implementation of InvestmentManagerRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS investment_managers (
                  manager_id TEXT PRIMARY KEY,
                  strategy_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  bio TEXT NOT NULL,
                  cohort TEXT NOT NULL,
                  deployed_at TEXT,
                  active INTEGER NOT NULL DEFAULT 0,
                  tagline TEXT NOT NULL DEFAULT '',
                  specialty TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS manager_nav (
                    manager_id TEXT NOT NULL,
                    nav_date TEXT NOT NULL,
                    equity REAL NOT NULL DEFAULT 0,
                    cash REAL NOT NULL DEFAULT 0,
                    total_fee REAL NOT NULL DEFAULT 0,
                    total_tax REAL NOT NULL DEFAULT 0,
                    note TEXT DEFAULT '',
                    PRIMARY KEY (manager_id, nav_date)
                );
                CREATE TABLE IF NOT EXISTS manager_trades (
                    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manager_id TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT DEFAULT '',
                    price REAL NOT NULL,
                    shares INTEGER NOT NULL,
                    fee REAL DEFAULT 0,
                    tax REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS manager_holdings_snap (
                    manager_id TEXT NOT NULL,
                    snap_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    shares INTEGER NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    entry_cost REAL NOT NULL DEFAULT 0,
                    high_px REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (manager_id, snap_date, symbol)
                );
                CREATE TABLE IF NOT EXISTS manager_position_state (
                    manager_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    shares INTEGER NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    entry_cost REAL NOT NULL DEFAULT 0,
                    high_px REAL NOT NULL DEFAULT 0,
                    entry_date TEXT NOT NULL,
                    PRIMARY KEY (manager_id, symbol)
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def get_manager(self, manager_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM investment_managers WHERE manager_id = ?", (manager_id,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def list_managers(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT * FROM investment_managers ORDER BY active DESC, deployed_at, manager_id")
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def upsert_manager(self, row: ManagerRow) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO investment_managers
                (manager_id, strategy_id, name, bio, cohort, deployed_at, active, tagline, specialty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(manager_id) DO UPDATE SET
                    strategy_id = excluded.strategy_id,
                    name = excluded.name,
                    bio = excluded.bio,
                    cohort = excluded.cohort,
                    tagline = excluded.tagline,
                    specialty = excluded.specialty
                """,
                (row.manager_id, row.strategy_id, row.name, row.bio, row.cohort, row.deployed_at, int(row.active), row.tagline, row.specialty),
            )
            conn.commit()
        finally:
            conn.close()

    def activate_next_batch(self, *, batch_size: int = 10) -> list[str]:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._connect()
        try:
            # Get inactive managers
            cur = conn.execute(
                "SELECT manager_id FROM investment_managers WHERE active = 0 ORDER BY manager_id LIMIT ?",
                (batch_size,)
            )
            rows = cur.fetchall()
            if not rows:
                return []
            
            ids = [r["manager_id"] for r in rows]
            # Update them to active
            conn.execute(
                "UPDATE investment_managers SET active = 1, deployed_at = ? WHERE manager_id IN ({})".format(
                    ",".join("?" for _ in ids)
                ),
                [now] + ids
            )
            conn.commit()
            return ids
        finally:
            conn.close()

    def upsert_nav(self, *, manager_id: str, nav_date: str, equity: float, cash: float, total_fee: float, total_tax: float, note: str = "") -> None:
        nd = nav_date[:10]
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO manager_nav (manager_id, nav_date, equity, cash, total_fee, total_tax, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(manager_id, nav_date) DO UPDATE SET
                    equity = excluded.equity,
                    cash = excluded.cash,
                    total_fee = excluded.total_fee,
                    total_tax = excluded.total_tax,
                    note = excluded.note
                """,
                (manager_id, nd, float(equity), float(cash), float(total_fee), float(total_tax), str(note or "")),
            )
            conn.commit()
        finally:
            conn.close()

    def get_nav_series(self, manager_id: str, *, limit: int = 420) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM manager_nav WHERE manager_id = ? ORDER BY nav_date DESC LIMIT ?",
                (manager_id, limit)
            )
            rows = cur.fetchall()
            result = [dict(r) for r in rows]
            result.reverse()
            return result
        finally:
            conn.close()

    def append_trade(self, payload: dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO manager_trades (manager_id, trade_date, symbol, action, reason, price, shares, fee, tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["manager_id"],
                    str(payload["trade_date"])[:19],
                    payload["symbol"],
                    payload["action"],
                    payload.get("reason") or "",
                    float(payload["price"]),
                    int(payload["shares"]),
                    float(payload.get("fee") or 0.0),
                    float(payload.get("tax") or 0.0)
                )
            )
            conn.commit()
        finally:
            conn.close()

    def list_trades(self, manager_id: str, *, limit: int = 400) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM manager_trades WHERE manager_id = ? ORDER BY trade_id DESC LIMIT ?",
                (manager_id, limit)
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def latest_holdings_snap_date_before(self, manager_id: str, snap_date: str) -> str | None:
        d = str(snap_date)[:10]
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT MAX(snap_date) FROM manager_holdings_snap WHERE manager_id = ? AND snap_date < ?",
                (manager_id, d)
            ).fetchone()
            return str(row[0])[:10] if row and row[0] else None
        finally:
            conn.close()

    def upsert_position_state(self, *, manager_id: str, symbol: str, shares: int, avg_cost: float, entry_cost: float, high_px: float, entry_date: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO manager_position_state (manager_id, symbol, shares, avg_cost, entry_cost, high_px, entry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(manager_id, symbol) DO UPDATE SET
                    shares = excluded.shares,
                    avg_cost = excluded.avg_cost,
                    entry_cost = excluded.entry_cost,
                    high_px = excluded.high_px,
                    entry_date = excluded.entry_date
                """,
                (manager_id, symbol, int(shares), float(avg_cost), float(entry_cost), float(high_px), str(entry_date)[:10]),
            )
            conn.commit()
        finally:
            conn.close()

    def trade_stats_by_manager(self) -> dict[str, dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT manager_id, COUNT(*) as trade_count, MAX(trade_date) as last_trade_date
                FROM manager_trades
                GROUP BY manager_id
                """
            )
            rows = cur.fetchall()
            result = {}
            for row in rows:
                result[row["manager_id"]] = {
                    "trade_count": row["trade_count"],
                    "last_trade_date": row["last_trade_date"] if row["last_trade_date"] else None
                }
            return result
        finally:
            conn.close()

    def get_holdings_snap(self, manager_id: str, snap_date: str) -> list[dict[str, Any]]:
        d = str(snap_date)[:10]
        if not d:
            return []
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM manager_holdings_snap WHERE manager_id = ? AND snap_date = ?",
                (manager_id, d)
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
